import os
from datetime import datetime, timedelta
from typing import Dict, List

import numpy as np
import torch
from torch.utils.data import DataLoader, RandomSampler, TensorDataset
from transformers import BertForSequenceClassification, BertTokenizer

_BATCH_SIZE = 16
_PRIORITY_ESTIMATOR_MODEL_PATH = os.environ.get("PRIORITY_ESTIMATOR_MODEL")
_MAX_LENGTH = 40
_PRIORITY_INT_TO_STR = {0: "Low", 1: "Medium", 2: "High"}


class PriorityEstimator:
    model = None
    tokenizer = None
    optimizer = None
    last_model_load = datetime.min

    @classmethod
    def initialize_priority_estimator(cls, force_init=False) -> None:
        if force_init or cls.last_model_load < (datetime.now() - timedelta(days=1)):
            cls.tokenizer = BertTokenizer.from_pretrained("bert-base-uncased", do_lower_case=True)
            cls.model = BertForSequenceClassification.from_pretrained(
                _PRIORITY_ESTIMATOR_MODEL_PATH
            )
            cls.optimizer = torch.optim.AdamW(cls.model.parameters(), lr=5e-5, eps=1e-08)
            cls.last_model_load = datetime.now()

    @classmethod
    def _preprocessing(cls, input_text: str) -> Dict:
        """
        Returns <class transformers.tokenization_utils_base.BatchEncoding> with the following fields:
        - input_ids: list of token ids
        - token_type_ids: list of token type ids
        - attention_mask: list of indices (0,1) specifying which tokens should considered by the model (return_attention_mask = True).
        """
        return cls.tokenizer.encode_plus(
            input_text,
            add_special_tokens=True,
            max_length=_MAX_LENGTH,
            pad_to_max_length=True,
            return_attention_mask=True,
            return_tensors="pt",
        )

    @classmethod
    def get_token_ids_and_attention_masks(cls, text: List[str]) -> torch.tensor:
        token_id = []
        attention_masks = []

        for sample in text:
            encoding_dict = cls._preprocessing(sample)
            token_id.append(encoding_dict["input_ids"])
            attention_masks.append(encoding_dict["attention_mask"])
        return torch.cat(token_id, dim=0), torch.cat(attention_masks, dim=0)

    @classmethod
    def _create_dataloader(cls, data: List[str], labels: List[int]) -> DataLoader:
        token_id, attention_masks = cls.get_token_ids_and_attention_masks(data)
        labels = torch.tensor(labels)  # pylint: disable=not-callable
        dataset = TensorDataset(token_id, attention_masks, labels)

        # Prepare DataLoader
        return DataLoader(dataset, sampler=RandomSampler(dataset), batch_size=_BATCH_SIZE)

    @classmethod
    def fit_to_data(cls, data: List[str], labels: List[int]) -> None:
        """
        Fits the model to given data and labels. Uploads newly trained model

        Params:
            data: list of strings such as "issue summary; feature; reporter"
                    Note, reporter should not have the "@duolingo.com" part
            labels: list of labels where 0 is Low, 1 is Medium, and 2 is High
        """
        cls.initialize_priority_estimator()
        train_dataloader = cls._create_dataloader(data, labels)
        cls.train_model(train_dataloader, epochs=1)
        cls.model.save_pretrained(_PRIORITY_ESTIMATOR_MODEL_PATH)

    @classmethod
    def train_model(cls, train_dataloader: DataLoader, epochs: int = 1) -> None:
        for _ in range(epochs):
            print("training model")
            # Set model to training mode
            cls.model.train()
            for batch in train_dataloader:
                b_input_ids, b_input_mask, b_labels = batch
                cls.optimizer.zero_grad()
                train_output = cls.model(  # pylint: disable=not-callable
                    b_input_ids,
                    attention_mask=b_input_mask,
                    labels=b_labels,
                )
                train_output.loss.backward()
                cls.optimizer.step()

    @classmethod
    def format_data(cls, sentence: str, feature: str, reporter: str) -> str:
        """
        Formats sentence, feature, and reporter into a single string

        Params
            sentence: string of text
            feature: Jira issue such as "WeChat"
            reporter: string of the issue reporter's email, such as biglou@duolingo.com
        """
        return f"{sentence}; {feature}; {cls.parse_reporter_email(reporter)}"

    @classmethod
    def _predict(cls, data: str) -> np.array:
        """
        Predicts priority scores for a given sentence, feature, and reporter

        Params
            data: string of the form "issue summary; feature; reporter"
                    Note, reporter should not have the "@duolingo.com" part

        Returns an np array of size 3 with a score for classes of Low, Medium, and High
        """
        encoding = cls._preprocessing(data)
        with torch.no_grad():
            output = cls.model(  # pylint: disable=not-callable
                encoding["input_ids"],
                attention_mask=encoding["attention_mask"],
            )

            return output.logits.cpu().numpy()

    @classmethod
    def estimate_priority(cls, sentence: str, feature: str = "", reporter_email: str = "") -> str:
        """
        Estimates the priority for a given sentence, Jira issue feature, and a reporter using pretrained Bert model
        Loads the model using PRIORITY_ESTIMATOR_MODEL environment variable

        Params
            sentence: string of text
            feature: Jira issue such as "WeChat"
            reporter_email: such as biglou@duolingo.com

        Returns a string representing estimated priority. Must be one of the vales of JiraPriority enum
        """
        cls.initialize_priority_estimator()
        data = cls.format_data(sentence, feature, reporter_email)
        prediction = cls._predict(data)
        return _PRIORITY_INT_TO_STR[np.argmax(prediction)]

    @classmethod
    def parse_reporter_email(cls, reporter_email: str):
        return reporter_email.split("@")[0] if reporter_email else ""

    @classmethod
    def evaluate(cls, data: List[str], labels: List[int]) -> float:
        """
        Runs the model on the data and returns the ratio of correctly predicted labels

        Params:
            data: list of strings such as "issue summary; feature; reporter"
                    Note, reporter should not have the "@duolingo.com" part
            labels: list of labels where 0 is Low, 1 is Medium, and 2 is High
        """
        cls.initialize_priority_estimator()
        eval_dataloader = cls._create_dataloader(data, labels)

        correct = 0
        total = 0
        cls.model.eval()
        with torch.no_grad():
            for batch in eval_dataloader:
                b_input_ids, b_input_mask, b_labels = batch

                output = cls.model(  # pylint: disable=not-callable
                    b_input_ids,
                    attention_mask=b_input_mask,
                )
                predictions = np.argmax(output.logits.cpu().numpy(), axis=1)
                correct += np.sum(predictions == b_labels.numpy())
                total += len(b_labels)
        return correct / len(data)
