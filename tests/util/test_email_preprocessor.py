import unittest

from jeeves.util.email_preprocessor import cleanup_email


class Test(unittest.TestCase):
    def test_quote_cue(self):
        body = (
            "Thanks for the invitation but this year I cannot afford going.\n"
            "On 22 May 2018, at 01:59, Duolingo Community Team wrote:\n"
            "Duolingo Global Ambassador Summit 2018 RSVP\n"
        )
        expected = "Thanks for the invitation but this year I cannot afford going."
        self.assertEqual(cleanup_email(body), expected)

    def test_separator(self):
        body = (
            "I will be unable to attend as it is in the middle of my school's exam period.\n"
            "________________________________\n"
            "From: Duolingo Community Team\n"
            "Sent: Tuesday, May 22, 2018 12:58:47 AM\n"
        )
        expected = "I will be unable to attend as it is in the middle of my school's exam period."
        self.assertEqual(cleanup_email(body), expected)

    def test_closing_cue(self):
        body = (
            "I'd like to be able to go one whole level at a time without stopping.\n\n"
            "Sincerely,\n"
            "Chief Product Officer\n"
        )
        expected = "I'd like to be able to go one whole level at a time without stopping.\n"
        self.assertEqual(cleanup_email(body), expected)
