import re
from typing import Tuple

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


_CLEANUP_PATTERN = _compile_cleanup_pattern()
_EMPTY_STRING_PATTERN = re.compile(r'^[\s\.,\?\\\/<>\(\)\+=_`~!@#\$%^&\*\[\]\{\}\|\'";:\-]*$')


_HYPHEN_LINE_PATTERN = re.compile("^[-\u2014]*$")


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
        print("No headers found, aborting.")
        return (body_text, {})

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
                        print("Error occured during subdata parsing, aborting.")
                        return (body_text, {})

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

    filtered_body_text = ""
    if rover_idx > 0:
        # We have actual body text
        filtered_body_text = "\n".join(body_lines[: rover_idx - 1])

    raw_metadata_text = "\n".join(body_lines[rover_idx:])
    extracted_metadata["raw"] = raw_metadata_text

    return (filtered_body_text, extracted_metadata)
