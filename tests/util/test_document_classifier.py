import unittest
from unittest.mock import MagicMock, patch

import numpy as np

from jeeves.util.document_classifier import JeevesDocumentClassifier

mock_model = MagicMock()


@patch("jeeves.util.document_classifier.JeevesDocumentClassifier.model", mock_model)
@patch("jeeves.util.document_classifier.JeevesDocumentClassifier._preprocessing", MagicMock())
@patch(
    "jeeves.util.document_classifier.JeevesDocumentClassifier._initialize_document_classifier",
    MagicMock(),
)
class Test(unittest.TestCase):
    def test_classify_document(self):
        mock_model.return_value.logits.cpu.return_value.numpy.return_value = np.array([[1, -0.6]])
        result = JeevesDocumentClassifier.classify_document("Example text")
        expected = False
        self.assertEqual(result, expected)

        mock_model.return_value.logits.cpu.return_value.numpy.return_value = np.array([[1, 1.2]])
        result = JeevesDocumentClassifier.classify_document("Example text")
        expected = True
        self.assertEqual(result, expected)
