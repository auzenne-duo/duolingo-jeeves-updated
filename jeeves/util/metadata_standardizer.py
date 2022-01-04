import re
from collections import defaultdict
from typing import DefaultDict, List, Match, Optional, Pattern

from jeeves.model.custom_types import JSON
from jeeves.util.language_code_mapping import LangCodeMap


class MetadataStandardizer:
    def __init__(self):

        # We're going to be using these regular expressions a lot so for the
        # sake of speed we pre-compile them once and then use them for every
        # document.

        lang_code_pattern = "((?:[A-Z][A-Z]-[A-Z][A-Z]) | (?:[A-Z][A-Z]) | (?:TLH))"
        direct_output_course_re = re.compile(
            f"DUOLINGO_{lang_code_pattern}_{lang_code_pattern}", re.X
        )
        course_codes_arrow_re = re.compile(f"{lang_code_pattern} <- {lang_code_pattern}", re.X)
        lang_names_arrow_re = re.compile("([^<]*) <- (.*)")
        self._course_re_list = [direct_output_course_re, course_codes_arrow_re, lang_names_arrow_re]

        self._fullstory_url_re_list = [re.compile("((?:https://)?app[.]fullstory[.]com/[^ ]*)")]

        apple_style_screen_size_re = re.compile("([0-9]+) W x ([0-9]+) H")
        general_screen_size_re = re.compile("([0-9]+)[ ]?x[ ]?([0-9]+)(?:, .*)?")
        self._screen_size_re_list = [apple_style_screen_size_re, general_screen_size_re]

        simple_ui_lang_re = re.compile("^([a-z][a-z])(?:[-_][0-9A-Za-z]{2,})?$")
        complex_ui_lang_re = re.compile(
            "[^:]*: ([a-z][a-z])(?:_[A-Za-z][A-Za-z])? : [a-z][a-z](?:_[A-Za-z][A-Za-z])?"
        )
        arrow_ui_lang_re = re.compile("^[a-z][a-z]<-([a-z][a-z])$")
        hans_ui_lang_re = re.compile("([a-z][a-z])-hans-[a-z][a-z]")

        self._ui_lang_re_list = [
            simple_ui_lang_re,
            complex_ui_lang_re,
            arrow_ui_lang_re,
            hans_ui_lang_re,
        ]

    def flatten_input_metadata(self, metadata_layer: JSON) -> JSON:
        """
        Given a JSON object that may contain nested JSON objects, produce a JSON
        object that contains no nested objects, and that contains every entry
        from the input object that was not itself an object. In other
        (possibly not exactly accurate) words, this discards all 'branch' nodes
        and returns a single object consisting only of 'leaf' nodes.

        Parameters:
            metadata_layer (JSON): A JSON object, that may or may not contain
                                   nested JSON objects.

        Returns:
            A JSON object containing every non-object element of the input,
            including elements inside nested objects at arbitrary depths,
            with all nesting removed.
        """

        layer_dict = {}
        for field in metadata_layer:
            if isinstance(metadata_layer[field], dict):
                sublayer_dict = self.flatten_input_metadata(metadata_layer[field])
                layer_dict.update(sublayer_dict)
            else:
                layer_dict[field] = metadata_layer[field]
        return layer_dict

    def _try_ordered_regular_expressions(
        self, flat_metadata: JSON, regex_list: List[Pattern], poss_fields: List[str]
    ) -> Optional[Match]:
        """
        Given a JSON object, attempts to match the values in each of several
        top-level fields against each of several regular expressions. If such
        a match is found, it is returned immediately and no further combinations
        are considered. Since the combinations are produced by simply iterating
        over the input lists, elements earlier in the list will be considered
        first. Accordingly, if there is overlap in match space between certain
        regular expressions, put the more specific or useful expressions earlier
        in the input list.

        Parameters:
            flat_metadata: JSON object, which must contain the fields in
                           poss_fields directly, without needing to look in
                           nested sub-objects.
            regex_list: List of compiled regular expressions to consider.
                        Expressions will be considered in the order given by
                        this list.
            poss_fields: Names of fields that will be extracted from the JSON
                         object, whose values will be compared against the
                         regular expressions.

        Returns:
            A match object corresponding to the first regular expression /
            field value match found, or None if no match is found with any
            combination of regular expression and field value.
        """
        for regex in regex_list:
            for f in poss_fields:
                match = regex.search(flat_metadata[f])
                if match:
                    return match
        return None

    def get_standardized_metadata(
        self, duolingo_metadata: JSON, aux_platform_information: str = ""
    ) -> DefaultDict[str, str]:
        """
        Extracts and standardizes certain fields from metadata information
        on (for example) shake-to-report documents. The standardized fields and
        formats are given below:

        app_version: Format depends on source
        course: DUOLINGO_<TO_LANGUAGE>_<FROM_LANGUAGE>
        fullstory_url: A link to https://app.fullstory.com
        os_version: Format depends on source
        platform: One of 'Android', 'iOS', or 'Web'
        screen_size: <WIDTH>x<HEIGHT>
        screen_content: Format depends on source
        ui_language: Two character language code, lowercase
        username: Any string that could be a Duolingo username

        There is a possible concern that multiple input fields could be picked
        up for mulitple standardized fields, such as a user's course information
        being stored in a field named 'course_language', which would also be
        considered for the standardized ui_language field. I examined about
        three months worth of documents and did not find any instances of this
        that affect the search criteria used in this function (as of Jan 2021)
        so I believe this is a nonissue for now.

        Parameters:
            duolingo_metadata: A JSON object returned from our shake-to-report
                               metadata extractor.
            aux_platform_information: An optional string that can be used to
                                      override calculation of the 'platform'
                                      field, if this value can be reliably
                                      determined outside this function.

        Returns:
            A defaultdict object containing as many of the standardized fields
            listed above as we are able to extract from the input metadata. If
            no fields are able to be extracted, including the case when the
            input metadata is empty, no fields will be set in the defaultdict
            before it is returned.
        """

        # Using a defaultdict instead of a dictionary is very nice because
        # we can treat the empty string as the value for "no entry",
        # so we only need to set entries that have values
        std_data = defaultdict(str)

        if aux_platform_information:
            std_data["platform"] = aux_platform_information

        if not duolingo_metadata:
            return std_data

        # There is possibly a concern that fields in different sub-objects
        # could have the same name when flattened, however I did not observe
        # any instances of this in the data I had available.
        flat_metadata = self.flatten_input_metadata(duolingo_metadata)

        possible_app_version_fields = [f for f in flat_metadata if "app_version" in f]
        if len(possible_app_version_fields) == 1:
            app_version_field = possible_app_version_fields[0]
            std_data["app_version"] = flat_metadata[app_version_field]

        possible_course_fields = [f for f in flat_metadata if "course" in f]
        course_match = self._try_ordered_regular_expressions(
            flat_metadata, self._course_re_list, possible_course_fields
        )
        if course_match and len(course_match.groups()) >= 2:
            to_lang = LangCodeMap.code_lookup(course_match.group(1))
            from_lang = LangCodeMap.code_lookup(course_match.group(2))

            if to_lang != "??" and from_lang != "??":
                std_data["course"] = f"DUOLINGO_{to_lang}_{from_lang}"

        possible_fullstory_fields = [f for f in flat_metadata if "fullstory" in f]
        if "session_url" in flat_metadata:
            possible_fullstory_fields.append("session_url")
        fullstory_match = self._try_ordered_regular_expressions(
            flat_metadata, self._fullstory_url_re_list, possible_fullstory_fields
        )
        if fullstory_match and len(fullstory_match.groups()) >= 1:
            std_data["fullstory_url"] = fullstory_match.group(1)

        if "ios_version" in flat_metadata:
            ios_ver = flat_metadata["ios_version"]
            if not ios_ver.startswith("iOS"):
                ios_ver = f"iOS {ios_ver}"
            std_data["os_version"] = ios_ver
        elif "os_version" in flat_metadata:
            std_data["os_version"] = flat_metadata["os_version"]
        elif "os" in flat_metadata:
            std_data["os_version"] = flat_metadata["os"]

        if not aux_platform_information:
            if "browser" in flat_metadata:
                std_data["platform"] = "Web"
            elif "ios_version" in flat_metadata:
                std_data["platform"] = "iOS"
            elif "api_level" in flat_metadata:
                std_data["platform"] = "Android"
            elif "platform" in flat_metadata and flat_metadata["platform"] in [
                "Android",
                "iOS",
                "Web",
            ]:
                std_data["platform"] = flat_metadata["platform"]

        possible_screen_size_fields = [f for f in flat_metadata if "screen" in f]
        screen_size_match = self._try_ordered_regular_expressions(
            flat_metadata, self._screen_size_re_list, possible_screen_size_fields
        )
        if screen_size_match and len(screen_size_match.groups()) >= 2:
            std_data["screen_size"] = f"{screen_size_match.group(1)}x{screen_size_match.group(2)}"

        if "url" in flat_metadata and std_data["platform"] == "Web":
            std_data["screen_content"] = flat_metadata["url"]
        elif "view_controller_name" in flat_metadata and std_data["platform"] == "iOS":
            std_data["screen_content"] = flat_metadata["view_controller_name"]
        elif "activity" in flat_metadata and std_data["platform"] == "Android":
            std_data["screen_content"] = flat_metadata["activity"]

        possible_ui_language_fields = [f for f in flat_metadata if "language" in f]
        ui_language_match = self._try_ordered_regular_expressions(
            flat_metadata, self._ui_lang_re_list, possible_ui_language_fields
        )
        if ui_language_match and len(ui_language_match.groups()) >= 1:
            std_data["ui_language"] = ui_language_match.group(1)

        if "username" in flat_metadata:
            std_data["username"] = flat_metadata["username"]

        return std_data


MetaStdizer = MetadataStandardizer()
