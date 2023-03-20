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
            "session_information": {
                "url": "https://www.duolingo.com/skill/ko/Onomatopoeia/1",
                "session_id": "KhIYBEcvkJioLxiT",
                "session_type": "lesson",
                "skill_tree_id": "36bab53b0938a448b9b5c9031c2021e5",
                "level_number": "1",
                "lesson_number": "0",
                "skill_name": "Onomatopoeia",
                "skill_id": "f0e3636eafacbd7a2c85e05c7ca0f5d7",
                "challenge_generator_id": "e74128efe39d77602f8535b8cd18cd64",
                "challenge_type": "translate",
                "challenge_generator_specific_type": "reverse_tap",
                "challenge_prompt_text": "After running to the school my heart was pounding.",
            },
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
            "challenge_id": "e74128efe39d77602f8535b8cd18cd64",
            "challenge_prompt_text": "After running to the school my heart was pounding.",
            "challenge_type": "translate",
            "challenge_generator_specific_type": "reverse_tap",
            "course": "DUOLINGO_KO_ZH-CN",
            "lesson_number": "0",
            "level_number": "1",
            "os_version": "iOS 13.6.1",
            "platform": "iOS",
            "screen_size": "414x896",
            "screen_content": "MatchChallengeVC",
            "session_id": "KhIYBEcvkJioLxiT",
            "session_type": "lesson",
            "skill_id": "f0e3636eafacbd7a2c85e05c7ca0f5d7",
            "skill_name": "Onomatopoeia",
            "skill_tree_id": "36bab53b0938a448b9b5c9031c2021e5",
            "ui_language": "en",
            "username": "mancyliao",
            "user_id": "574989974",
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
                "challenge_id": "2175bfb7e13345ebbbafbd6d3a0ab4c2",
                "challenge_prompt_text": "None of you wants to buy clothes?",
                "challenge_type": "translate",
                "ios_v2_dev": "false",
                "lesson_number": "0",
                "level_number": "1",
                "path_level_debug_name": "n/a",
                "path_level_id": "n/a",
                "path_level_specifics": "[:]",
                "path_level_type": "n/a",
                "service_mappings": "none",
                "session_bundle_id": "en_es_b2c93919b31cde56b1972f5f18ca9a72_level.1.0",
                "session_id": "S87ajXxr3b72d08i",
                "session_information": "",
                "session_type": "lesson",
                "skill_id": "b2c93919b31cde56b1972f5f18ca9a72",
                "skill_tree_id": "7eb9f55873194e20f1a3bba34c35d734",
                "user_input_text": "Ninguno de ustedes quiere comprar ropa",
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
            "challenge_id": "2175bfb7e13345ebbbafbd6d3a0ab4c2",
            "challenge_prompt_text": "None of you wants to buy clothes?",
            "challenge_type": "translate",
            "lesson_number": "0",
            "level_number": "1",
            "session_bundle_id": "en_es_b2c93919b31cde56b1972f5f18ca9a72_level.1.0",
            "session_id": "S87ajXxr3b72d08i",
            "session_type": "lesson",
            "skill_id": "b2c93919b31cde56b1972f5f18ca9a72",
            "skill_tree_id": "7eb9f55873194e20f1a3bba34c35d734",
            "user_id": "107934822",
        }
        self.assertEqual(expected_real_2, MetaStdizer.get_standardized_metadata(real_metadata_2))

        real_birdseye_metadata = {
            "app_information": {
                "screen": "shop-tab",
                "app_version": "6.099.0",
                "platform": "iOS",
                "device": "iPhone SE",
                "languages": "en<-dn",
                "workflow": "shop",
            },
        }
        expected_real_birdseye = {
            "app_version": "6.099.0",
            "platform": "iOS",
            "ui_language": "dn",
        }
        self.assertEqual(
            expected_real_birdseye, MetaStdizer.get_standardized_metadata(real_birdseye_metadata)
        )

        empty_input = {}
        expected_empty_output = {}
        self.assertEqual(expected_empty_output, MetaStdizer.get_standardized_metadata(empty_input))

        expected_non_empty_output = {"platform": "Web"}
        self.assertEqual(
            expected_non_empty_output, MetaStdizer.get_standardized_metadata(empty_input, "Web")
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
