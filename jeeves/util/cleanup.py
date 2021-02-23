import re
from typing import Pattern, Tuple

from jeeves.model.custom_types import JSON
from jeeves.util.metadata import parse_metadata


def _compile_cleanup_pattern():
    METADATA_FRIENDS_REGEX = r"-{3,}\s+App information:[\s\S]+?-{3,}|[A-z\-_\.]+\.txt"
    SIGNATURE_REGEX = r'^[\s\.,\?\\\/<>\(\)\+=_`~!@#\$%^&\*\[\]\{\}\|\'";:\-]*(?:Sent (?:from|via)|Enviado desde) .*$'
    URL_REGEX = (
        # protocol identifier
        r"(?:(?:https?|ftp)://)"
        # user:pass authentication
        + r"(?:\S+(?::\S*)?@)?"
        + r"(?:"
        # IP address exclusion
        # private & local networks
        + r"(?!(?:10|127)(?:\.\d{1,3}){3})"
        + r"(?!(?:169\.254|192\.168)(?:\.\d{1,3}){2})"
        + r"(?!172\.(?:1[6-9]|2\d|3[0-1])(?:\.\d{1,3}){2})"
        # IP address dotted notation octets
        # excludes loopback network 0.0.0.0
        # excludes reserved space >= 224.0.0.0
        # excludes network & broadcast addresses
        # (first & last IP address of each class)
        + r"(?:[1-9]\d?|1\d\d|2[01]\d|22[0-3])"
        + r"(?:\.(?:1?\d{1,2}|2[0-4]\d|25[0-5])){2}"
        + r"(?:\.(?:[1-9]\d?|1\d\d|2[0-4]\d|25[0-4]))"
        + r"|"
        # host name
        + r"(?:(?:[a-z\u00a1-\uffff0-9]-?)*[a-z\u00a1-\uffff0-9]+)"
        # domain name
        + r"(?:\.(?:[a-z\u00a1-\uffff0-9]-?)*[a-z\u00a1-\uffff0-9]+)*"
        # TLD identifier
        + r"(?:\.(?:[a-z\u00a1-\uffff]{2,}))"
        + r")"
        # port number
        + r"(?::\d{2,5})?"
        # resource path
        + r"(?:/\S*)?"
    )

    # CSS_REGEX = r'(\w+)?(\s*>\s*)?(#\w+)?\s*(\.\w+)?(\s*,\s*(\w+)?(\s*>\s*)?(#\w+)?\s*(\.\w+)?)*\s*\{\s*(\s*[\w\-_]+\s*:\s*[^;]+?\s*;)*\s*\}'

    CLEANUP = re.compile(
        r"|".join([METADATA_FRIENDS_REGEX, SIGNATURE_REGEX, URL_REGEX]),  # , CSS_REGEX]
        re.UNICODE | re.IGNORECASE | re.MULTILINE,
    )
    return CLEANUP


_COMMON_ZENDESK_META_HEADER_LIST = [
    "Username",
    "Learning language",
    "Course",
    "uFlags",
    "App version",
    "Device model",
    "Raw Platform",
    "Platform",
    "OS version",
    "UI language",
]


def _compile_common_zendesk_header_re() -> Pattern:
    """
    Compiles regular expression used to search for a sequence of metadata
    headers that are common to many Zendesk documents. Intended to only be
    called once, when this module is first loaded.

    Parameters: None

    Returns:
        Compiled regular expression corresponding to a sequence of common
        metadata headers
    """

    # Add a colon, capturing group, and end-of-line check to each header
    prepared_lines = [f"{header}: (.*?)$" for header in _COMMON_ZENDESK_META_HEADER_LIST]

    # Add arbitrary whitespace and beginning-of-line check between each header.
    # We put the beginning-of-line check here instead of on every header since
    # some documents have the first header begin on the same line as text that
    # isn't metadata, so we don't want a beginning-of-line check on the first
    # header.
    complete_pattern = "\s*?^".join(prepared_lines)

    return re.compile(complete_pattern, re.MULTILINE)


_CLEANUP_PATTERN = _compile_cleanup_pattern()
_EMPTY_STRING_PATTERN = re.compile(r'^[\s\.,\?\\\/<>\(\)\+=_`~!@#\$%^&\*\[\]\{\}\|\'";:\-]*$')


_HYPHEN_LINE_PATTERN = re.compile("^[-\u2014]+$")

_COMMON_ZENDESK_META_PATTERN = _compile_common_zendesk_header_re()


def clean_and_parse_description(desc):
    """
    Cleans description and parses out metadata dictionary

    Arguments:
        desc {str} -- Support Ticket description

    Returns:
        (str, dict) -- Tuple of cleaned description and metadata dictionary
    """

    # first parse and cut out metadata, then cleanup rest of description for
    cutDesc, mdict = parse_metadata(desc + "\n")
    return _EMPTY_STRING_PATTERN.sub("", _CLEANUP_PATTERN.sub("", cutDesc.strip())), mdict


def check_for_hyphen_line(body_text: str) -> bool:
    """
    Checks if a string contains a line that consists only of hyphen characters.
    This will be used as a cheap and reasonably accurate way to check if a
    document contains metadata information in its description, without needing
    to fully parse the potential metadata.

    Parameters:
        body_text: Description string which we wish to check for hypen line.

    Returns:
        True if the input contains a line of just hyphens, otherwise False.
    """

    body_lines = [line.strip() for line in body_text.split("\n")]
    return any([bool(_HYPHEN_LINE_PATTERN.match(line)) for line in body_lines])


def extract_duolingo_metadata(body_text: str) -> Tuple[str, JSON]:
    """
    Separates beta feedback metadata from the downloaded body text of a record
    and returns them as separate objects.

    Parameters:
        body_text: Description section of a document that we wish to clean

    Returns:
        A two-tuple where the first element is the body text with the metadata
        removed and the second element is the metadata as JSON. If a problem
        occurs during parsing, instead return the body text untouched and an
        empty tuple.
    """

    extracted_metadata = {}

    single_value_headers = ["Report method:", "View Controller Name:"]
    multi_value_headers = [
        "System Information:",
        "User Information:",
        "App Information:",
        "App information:",
        "Session information:",
        "FullStory:",
    ]
    known_headers = single_value_headers + multi_value_headers

    body_lines = [line.strip() for line in body_text.split("\n")]

    present_headers = []
    for line in body_lines:
        if line in known_headers:
            if line in present_headers:
                print(f"Header {line} appeared twice, aborting.")
                return (body_text, {})
            present_headers.append(line)

    if not present_headers:
        return (body_text, {})

    max_data_idx = 0

    # Now we collect the data for each header. For multi-value headers,
    # we know we're done collecting data when we reach another header,
    # a line consisting only of hyphens, or the end of the document.
    for header in present_headers:
        header_idx = body_lines.index(header)
        # The header names as I have them hard-coded include a colon at the end,
        # but we don't want that colon included in the Elasticsearch field name.
        processed_field_name = header[:-1].replace(" ", "_").lower()

        if header in single_value_headers:
            field_value = body_lines[header_idx + 1]
            extracted_metadata[processed_field_name] = field_value

        elif header in multi_value_headers:
            sub_dict = {}
            data_idx = header_idx
            while True:
                data_idx += 1

                if data_idx >= len(body_lines):
                    break

                max_data_idx = data_idx

                line = body_lines[data_idx]
                if not line:
                    continue

                if _HYPHEN_LINE_PATTERN.match(line):
                    break
                if line in known_headers:
                    break

                if line.startswith("-"):
                    line = line[1:].strip()

                colon_idx = line.find(":")
                if colon_idx < 0:
                    if header == "FullStory:" and "No session recorded" in line:
                        sub_dict["fullstory"] = line
                    else:
                        max_data_idx -= 1
                        break

                key_str = (
                    line[:colon_idx].replace(" ", "_").replace("(", "").replace(")", "").lower()
                )
                value_str = line[colon_idx + 1 :].strip()

                sub_dict[key_str] = value_str

                if key_str == "tags":
                    value_list = value_str.split()
                    sub_dict[key_str] = value_list

            extracted_metadata[processed_field_name] = sub_dict

    # To separate off the actual body text, take the earliest header and work
    # backward until we find a line of all hyphens. The line before that is the
    # last line of body text.
    rover_idx = body_lines.index(present_headers[0]) - 1
    line = body_lines[rover_idx]
    while rover_idx >= 0 and not _HYPHEN_LINE_PATTERN.match(line):
        rover_idx -= 1
        line = body_lines[rover_idx]

    filtered_body_text_prologue = ""
    if rover_idx > 0:
        # We have actual body text
        filtered_body_text_prologue = "\n".join(body_lines[: rover_idx - 1]).strip()

    filtered_body_text_epilogue = ""
    if max_data_idx < len(body_lines):
        filtered_body_text_epilogue = "\n".join(body_lines[max_data_idx + 1 :]).strip()

    filtered_body_text = f"{filtered_body_text_prologue}\n{filtered_body_text_epilogue}"

    raw_metadata_text = "\n".join(body_lines[rover_idx : max_data_idx + 1])
    extracted_metadata["raw"] = raw_metadata_text

    return (filtered_body_text, extracted_metadata)


def extract_common_zendesk_headers(body_text: str) -> Tuple[str, JSON]:
    """
    Checks for a specific combination and ordering of known metadata headers
    in provided body text. If found, parses out the metadata and returns the
    cleaned body text and parsed metadata as separate objects.

    Checking for specific headers in a specific order goes against the spirit
    of the parsing function I already put in this file. However, in some limited
    testing, these headers in this order appeared in over 90% of the Zendesk
    documents we couldn't parse with the existing method, and I would rather
    Ship It than come up with one method that works on both cases.

    Parameters:
        body_text: Description section of a document that we wish to clean

    Returns:
        A two-tuple where the first element is the body text with the metadata
        removed and the second element is the metadata as JSON. If the body text
        cannot be parsed, instead the first element will be the unmodified body
        text and the second element will be an empty dictionary.
    """

    m = _COMMON_ZENDESK_META_PATTERN.search(body_text)

    if not m:
        return (body_text, {})

    keys = [header.replace(" ", "_").lower() for header in _COMMON_ZENDESK_META_HEADER_LIST]
    values = list(m.groups())
    if len(keys) != len(values):
        return (body_text, {})

    kv_pairs = zip(keys, values)
    parsed_metadata = {key: val for (key, val) in kv_pairs}

    prologue = body_text[: m.start()].strip()
    epilogue = body_text[m.end() :].strip()
    filtered_body_text = f"{prologue}\n{epilogue}"

    return (filtered_body_text, parsed_metadata)
