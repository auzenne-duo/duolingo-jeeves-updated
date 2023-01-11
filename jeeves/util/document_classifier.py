import os
from datetime import datetime
from math import exp
from typing import Dict, List

import numpy as np
import torch
from transformers import BertForSequenceClassification, BertTokenizer

_BUG_REPORT_THRESHOLD = 0.4
_JEEVES_DOCUMENT_CLASSIFIER_PATH = os.environ.get("JEEVES_DOCUMENT_CLASSIFIER")
_MAX_LENGTH = 40


class JeevesDocumentClassifier:
    model = None
    tokenizer = None
    optimizer = None
    last_model_load = datetime.min

    @classmethod
    def _initialize_document_classifier(cls) -> None:
        if cls.model is None:
            cls.tokenizer = BertTokenizer.from_pretrained("bert-base-uncased", do_lower_case=True)
            cls.model = BertForSequenceClassification.from_pretrained(
                _JEEVES_DOCUMENT_CLASSIFIER_PATH
            )

    @classmethod
    def _preprocessing(cls, input_text: str) -> Dict:
        """
        Returns a dict with the following fields:
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
    def _predict(cls, data: str) -> np.array:
        """
        Predicts priority scores for a given text

        Params
            data: string of a Jeeves document body text

        Returns an np array of size 2 with a score for classes of is_bug, is_not_bug
        """
        encoding = cls._preprocessing(data)
        with torch.no_grad():
            output = cls.model(  # pylint: disable=not-callable
                encoding["input_ids"],
                attention_mask=encoding["attention_mask"],
            )

            return output.logits.cpu().numpy()

    @classmethod
    def classify_document(cls, body_text: str) -> bool:
        """
        Returns True if the document is predicted to be a bug report, else False
        """
        cls._initialize_document_classifier()
        prediction = cls._predict(body_text)

        # Bert model uses cross entropy loss to predict class
        bug_report_probability = exp(prediction[0][1]) / (
            exp(prediction[0][0]) + exp(prediction[0][1])
        )
        return bug_report_probability > _BUG_REPORT_THRESHOLD
