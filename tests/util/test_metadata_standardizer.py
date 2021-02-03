import unittest

from jeeves.util.metadata_standardizer import MetaStdizer


class Test(unittest.TestCase):
    def test_flatten_input_metadata(self):
        input_dict = {}
        expected_dict = {}
        output_dict = MetaStdizer.flatten_input_metadata(input_dict)
        self.assertEqual(output_dict, expected_dict)

        input_dict = {"a": "a"}
        expected_dict = {"a": "a"}
        output_dict = MetaStdizer.flatten_input_metadata(input_dict)
        self.assertEqual(output_dict, expected_dict)

        input_dict = {"a": "a", "a2": {}}
        expected_dict = {"a": "a"}
        output_dict = MetaStdizer.flatten_input_metadata(input_dict)
        self.assertEqual(output_dict, expected_dict)

        input_dict = {"a": "a", "a2": {"b": "b"}}
        expected_dict = {"a": "a", "b": "b"}
        output_dict = MetaStdizer.flatten_input_metadata(input_dict)
        self.assertEqual(output_dict, expected_dict)

        input_dict = {"a": {"b": {"c": {"d": {"e": {"f": {}}}}}}}
        expected_dict = {}
        output_dict = MetaStdizer.flatten_input_metadata(input_dict)
        self.assertEqual(output_dict, expected_dict)

        input_dict = {"a": {"b": {"c": {"d": {"e": {"f": "f"}}}}}}
        expected_dict = {"f": "f"}
        output_dict = MetaStdizer.flatten_input_metadata(input_dict)
        self.assertEqual(output_dict, expected_dict)

        input_dict = {"a": {"b": {"c": "c", "c2": {"d": {"e": {"f": "f"}}}}}}
        expected_dict = {"c": "c", "f": "f"}
        output_dict = MetaStdizer.flatten_input_metadata(input_dict)
        self.assertEqual(output_dict, expected_dict)

    def test_get_standardized_metadata(self):

        real_metadata_1 = {
            "system_information": {
                "app_version": "6.97.2.3",
                "ios_version": "13.6.1",
                "device_model": "iPhone",
                "platform": "iPhone XR",
                "raw_platform": "iPhone11,8",
                "ui_language": "en-us",
                "screen": "414 W x 896 H",
                "environment": "App Store (com.duolingo.DuolingoMobile)",
                "jail_broken": "false",
            },
            "user_information": {
                "id": "574989974",
                "email": "mancy@duolingo.com",
                "username": "mancyliao",
                "current_course": "DUOLINGO_KO_ZH-CN (Chinese -> Korean)",
                "time_zone": "America/New_York",
            },
            "report_method": "screenshot",
            "view_controller_name": "MatchChallengeVC",
            "fullstory": "",
        }
        expected_real_1 = {
            "app_version": "6.97.2.3",
            "course": "DUOLINGO_KO_ZH-CN",
            "os_version": "iOS 13.6.1",
            "platform": "iOS",
            "screen_size": "414x896",
            "screen_content": "MatchChallengeVC",
            "ui_language": "en",
            "username": "mancyliao",
        }
        self.assertEqual(expected_real_1, MetaStdizer.get_standardized_metadata(real_metadata_1))

        real_metadata_2 = {
            "system_information": {
                "app_version": "6.94.0.4",
                "ios_version": "14.2",
                "device_model": "iPhone",
                "platform": "iPhone 8 Plus (Model A1864)",
                "raw_platform": "iPhone10,2",
                "ui_language": "en-us",
                "screen": "414 W x 736 H",
                "environment": "Test Flight (com.duolingo.DuolingoMobile)",
                "jail_broken": "false",
            },
            "user_information": {
                "id": "107934822",
                "email": "museberry3@hotmail.com",
                "username": "AnjuliGlobal",
                "current_course": "DUOLINGO_FR_EN (English -> French)",
                "time_zone": "America/New_York",
            },
            "report_method": "screenshot",
            "view_controller_name": "UIViewController",
            "fullstory": {
                "session_url": "https://app.fullstory.com/ui/QZHJ3/session/4707865639829504:4870003962331136"
            },
        }
        expected_real_2 = {
            "app_version": "6.94.0.4",
            "course": "DUOLINGO_FR_EN",
            "fullstory_url": "https://app.fullstory.com/ui/QZHJ3/session/4707865639829504:4870003962331136",
            "os_version": "iOS 14.2",
            "platform": "iOS",
            "screen_size": "414x736",
            "screen_content": "UIViewController",
            "ui_language": "en",
            "username": "AnjuliGlobal",
        }
        self.assertEqual(expected_real_2, MetaStdizer.get_standardized_metadata(real_metadata_2))

        empty_input = {}
        expected_empty_output = {}
        self.assertEqual(expected_empty_output, MetaStdizer.get_standardized_metadata(empty_input))
        self.assertEqual(
            expected_empty_output, MetaStdizer.get_standardized_metadata(empty_input, "Web")
        )

        good_size_input = {"pixels_in_screen": "1920 W x 1080 H"}
        expected_good_size_output = {"screen_size": "1920x1080"}
        self.assertEqual(
            expected_good_size_output, MetaStdizer.get_standardized_metadata(good_size_input)
        )

        bad_size_input = {"pixels_in_screen": "Nope this data is garbage"}
        self.assertEqual(
            expected_empty_output, MetaStdizer.get_standardized_metadata(bad_size_input)
        )

        platform_auto_detect_input = {"api_level": "30"}
        expected_auto_detect_output = {"platform": "Android"}
        self.assertEqual(
            expected_auto_detect_output,
            MetaStdizer.get_standardized_metadata(platform_auto_detect_input),
        )

        expected_override_output = {"platform": "Web"}
        self.assertEqual(
            expected_override_output,
            MetaStdizer.get_standardized_metadata(platform_auto_detect_input, "Web"),
        )
