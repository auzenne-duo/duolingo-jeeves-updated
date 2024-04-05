"""
Unit test for cleanup util.
"""
import unittest

from jeeves.util.cleanup import clean_and_parse_description, extract_common_zendesk_headers


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

    def test_extract_common_zendesk_headers(self):
        empty_test_input = ""
        empty_test_expected = ("", {})
        empty_test_result = extract_common_zendesk_headers(empty_test_input)
        self.assertEqual(empty_test_result, empty_test_expected)

        useless_test_input = "The quick brown fox"
        useless_test_expected = (useless_test_input, {})
        useless_test_result = extract_common_zendesk_headers(useless_test_input)
        self.assertEqual(useless_test_result, useless_test_expected)

        real_test_input = "Please discontinue the “Practice Complete” feature with the points calculator as it is a waste of learning time with no real benefit at all. It is very frustrating to have to sit and watch that feature so many times over and over during lessons. Waiting for it to finish is truly a waste of time that could be better spent learning. It is also irritating that you have to tap twice to continue when it is over. \n\nI am a Plus member who is serious about devoting time to learning French with Duo. \n\nThank you. \n\nKathryn Gerth\n\n\n\nUsername: Kathryn836594\nLearning language: fr\nCourse: DUOLINGO_FR_EN\nuFlags: PS6T3BRN PU0310K4\nApp version: 6.103.0.3\nDevice model: iPhone\nRaw Platform: iPhone13,2\nPlatform: iPhone13,2\nOS version: 14.4\nUI language: en-us\nlogs.txt\nSent from my iPhone"
        real_test_expected = (
            "Please discontinue the “Practice Complete” feature with the points calculator as it is a waste of learning time with no real benefit at all. It is very frustrating to have to sit and watch that feature so many times over and over during lessons. Waiting for it to finish is truly a waste of time that could be better spent learning. It is also irritating that you have to tap twice to continue when it is over. \n\nI am a Plus member who is serious about devoting time to learning French with Duo. \n\nThank you. \n\nKathryn Gerth\nlogs.txt\nSent from my iPhone",
            {
                "username": "Kathryn836594",
                "learning_language": "fr",
                "course": "DUOLINGO_FR_EN",
                "uflags": "PS6T3BRN PU0310K4",
                "app_version": "6.103.0.3",
                "device_model": "iPhone",
                "raw_platform": "iPhone13,2",
                "platform": "iPhone13,2",
                "os_version": "14.4",
                "ui_language": "en-us",
            },
        )
        real_test_result = extract_common_zendesk_headers(real_test_input)
        self.assertEqual(real_test_result, real_test_expected)

        adjacent_test_input = "Hello:\n\nI would like a refund please. I have just had a baby and I am working full time and unfortunately unable to use this subscription at this point in time. Please help! \n\nThank you,\n\nKayla (Fava) Sangster\n\n\n\n-------------------\nApp Information:\nUsername: KaylaMarie980480\nLearning language: es\nCourse:\nUI language: en\nuFlags: LITNBU2T\nUserId: 12345\n-------------------"
        adjacent_test_expected_body = "Hello:\n\nI would like a refund please. I have just had a baby and I am working full time and unfortunately unable to use this subscription at this point in time. Please help! \n\nThank you,\n\nKayla (Fava) Sangster\n\n\n\n-------------------\nApp Information:\n-------------------"
        adjacent_test_expected = (
            adjacent_test_expected_body,
            {
                "username": "KaylaMarie980480",
                "learning_language": "es",
                "course": "",
                "ui_language": "en",
                "uflags": "LITNBU2T",
                "userid": "12345",
            },
        )
        adjacent_test_result = extract_common_zendesk_headers(adjacent_test_input)
        self.assertEqual(adjacent_test_result, adjacent_test_expected)


if __name__ == "__main__":
    unittest.main()
