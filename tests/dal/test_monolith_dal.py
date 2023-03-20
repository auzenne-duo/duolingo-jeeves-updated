import unittest
from unittest.mock import MagicMock, patch

from jeeves.dal.monolith_dal import MonolithDAL

mock_requests = MagicMock()


@patch("jeeves.dal.monolith_dal.requests", mock_requests)
class TestElasticSearchInterface(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestElasticSearchInterface, self).__init__(*args, **kwargs)
        self.dal = MonolithDAL()

    def test_get_user_by_email_or_username(self):
        mock_requests.get.return_value.json.return_value = {"users": [{"id": 1010}]}
        result = self.dal.get_user_by_email_or_username("anotherfake@fake.com")
        expected = 1010
        self.assertEqual(result, expected)

    def test_get_user_by_email_or_username_multiple_results(self):
        mock_requests.get.return_value.json.return_value = {"users": [{"id": 1010}, {"id": 2323}]}
        result = self.dal.get_user_by_email_or_username("anotherfake@fake.com")
        expected = None
        self.assertEqual(result, expected)

    def test_get_user_by_email_or_username_no_results(self):
        mock_requests.get.return_value.json.return_value = {"users": []}
        result = self.dal.get_user_by_email_or_username("fake_email@fake.com")
        expected = None
        self.assertEqual(result, expected)

    def test_get_user_by_email_or_username_no_input(self):
        self.assertRaises(AssertionError, self.dal.get_user_by_email_or_username)
