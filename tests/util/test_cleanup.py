"""
Unit test for cleanup util.
"""
import unittest

from jeeves.util.cleanup import clean_and_parse_description


class Test(unittest.TestCase):

    def test_clean_description(self):
        description = r"""I don't have a problem with the functionality of the app but it kept on
        displaying somewhat adult but sensored pictures.
        I always forget to take screenshots but I was able to get one today.
        It had been happening for a while now. Please look into this or have an option for us users
        to flag or report an ad showing on the app. What if a kid sees that?

        lease see attachment.
        Thank you very much.

        Regards,

        Onat
        -------------------
        App information:
        App version code: 3.41.1 googleAllcourses
        API Level: 22
        OS Version: 3.10.65-user (1464266312)
        Host (Device): mz-builder-2 (m2note)
        Model (Product): m2 note (m2note)
        Screen: 1080x1920, 480dpi
        Config: Internal, 256 | 256
        Username: ronturon
        Languages: es<-en : en : en_US
        -------------------"""
        expected = r"""I don't have a problem with the functionality of the app but it kept on
        displaying somewhat adult but sensored pictures.
        I always forget to take screenshots but I was able to get one today.
        It had been happening for a while now. Please look into this or have an option for us users
        to flag or report an ad showing on the app. What if a kid sees that?

        lease see attachment.
        Thank you very much.

        Regards,

        Onat
        """
        result, _ = clean_and_parse_description(description)
        self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()
