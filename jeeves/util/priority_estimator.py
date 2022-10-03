import os
from typing import Dict, List

import numpy as np
import torch
from torch.utils.data import DataLoader, RandomSampler, TensorDataset
from transformers import BertForSequenceClassification, BertTokenizer

from jeeves.config.config import PRIORITY_ESTIMATOR_S3_PATH
from jeeves.util.s3_client_and_bucket import get_s3_client_and_bucket

BATCH_SIZE = 16
_PRIORITY_ESTIMATOR_MODEL_PATH = os.environ.get("PRIORITY_ESTIMATOR_MODEL")
MAX_LENGTH = 40

PRIORITY_STR_TO_INT = {"Low": 0, "Lowest": 0, "Medium": 1, "High": 2, "Highest": 2}
PRIORITY_INT_TO_STR = {0: "Low", 1: "Medium", 2: "High"}


class PriorityEstimator:
    model = None
    tokenizer = None
    optimizer = None

    @classmethod
    def _initialize_priority_estimator(cls) -> None:
        if cls.model is None:
            cls.tokenizer = BertTokenizer.from_pretrained("bert-base-uncased", do_lower_case=True)
            cls.model = BertForSequenceClassification.from_pretrained(
                _PRIORITY_ESTIMATOR_MODEL_PATH
            )
            cls.optimizer = torch.optim.AdamW(cls.model.parameters(), lr=5e-5, eps=1e-08)

    @classmethod
    def preprocessing(cls, input_text: str) -> Dict:
        """
        Returns <class transformers.tokenization_utils_base.BatchEncoding> with the following fields:
        - input_ids: list of token ids
        - token_type_ids: list of token type ids
        - attention_mask: list of indices (0,1) specifying which tokens should considered by the model (return_attention_mask = True).
        """
        return cls.tokenizer.encode_plus(
            input_text,
            add_special_tokens=True,
            max_length=MAX_LENGTH,
            pad_to_max_length=True,
            return_attention_mask=True,
            return_tensors="pt",
        )

    @classmethod
    def get_token_ids_and_attention_masks(cls, text: List[str]) -> torch.tensor:
        token_id = []
        attention_masks = []

        for sample in text:
            encoding_dict = cls.preprocessing(sample)
            token_id.append(encoding_dict["input_ids"])
            attention_masks.append(encoding_dict["attention_mask"])
        return torch.cat(token_id, dim=0), torch.cat(attention_masks, dim=0)

    @classmethod
    def fit_to_data(cls, data: List[str], labels: List[int]) -> None:
        """
        Fits the model to given data and labels. Uploads newly trained model

        Params:
            data: list of strings such as "issue summary; feature; reporter"
                    Note, reporter should not have the "@duolingo.com" part
            labels: list of labels where 0 is Low, 1 is Medium, and 2 is High
        """
        s3_client, s3_bucket_name = get_s3_client_and_bucket()
        cls._initialize_priority_estimator()
        token_id, attention_masks = cls.get_token_ids_and_attention_masks(data)
        labels = torch.tensor(labels)  # pylint: disable=not-callable
        train_set = TensorDataset(token_id, attention_masks, labels)

        # Prepare DataLoader
        train_dataloader = DataLoader(
            train_set, sampler=RandomSampler(train_set), batch_size=BATCH_SIZE
        )
        cls.train_model(train_dataloader, epochs=1)
        cls.model.save_pretrained(_PRIORITY_ESTIMATOR_MODEL_PATH)
        for filename in os.listdir(_PRIORITY_ESTIMATOR_MODEL_PATH):
            filepath = os.path.join(_PRIORITY_ESTIMATOR_MODEL_PATH, filename)
            with open(filepath, "rb") as f:
                s3_client.upload(
                    s3_bucket_name, os.path.join(PRIORITY_ESTIMATOR_S3_PATH, filename), f.read()
                )
            os.remove(filepath)

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
    def predict(cls, sentence: str, feature: str, reporter: str) -> np.array:
        """
        Predicts priority scores for a given sentence, feature, and reporter

        Params
            sentence: string of text
            feature: Jira issue such as "WeChat"
            reporter: username string of the issue reporter. The username part of an email, such as biglou

        Returns an np array of size 3 with a score for classes of Low, Medium, and High
        """
        encoding = cls.preprocessing(f"{sentence}; {feature}; {reporter}")
        with torch.no_grad():
            output = cls.model(  # pylint: disable=not-callable
                encoding["input_ids"],
                token_type_ids=None,
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
        cls._initialize_priority_estimator()
        prediction = cls.predict(sentence, feature, cls.parse_reporter_email(reporter_email))
        return PRIORITY_INT_TO_STR[np.argmax(prediction)]

    @classmethod
    def parse_reporter_email(cls, reporter_email: str):
        return reporter_email.split("@")[0] if reporter_email else ""
