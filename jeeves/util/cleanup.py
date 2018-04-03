import re

from jeeves.util.metadata import parse_metadata


def _compile_cleanup_pattern():
    METADATA_FRIENDS_REGEX = r'-{3,}\s+App information:[\s\S]+?-{3,}|[A-z\-_\.]+\.txt'
    SIGNATURE_REGEX = r'^[\s\.,\?\\\/<>\(\)\+=_`~!@#\$%^&\*\[\]\{\}\|\'";:\-]*(?:Sent (?:from|via)|Enviado desde) .*$'
    URL_REGEX = (
        # protocol identifier
        r"(?:(?:https?|ftp)://)"
        # user:pass authentication
        + r"(?:\S+(?::\S*)?@)?" + r"(?:"
        # IP address exclusion
        # private & local networks
        + r"(?!(?:10|127)(?:\.\d{1,3}){3})" + r"(?!(?:169\.254|192\.168)(?:\.\d{1,3}){2})" +
        r"(?!172\.(?:1[6-9]|2\d|3[0-1])(?:\.\d{1,3}){2})"
        # IP address dotted notation octets
        # excludes loopback network 0.0.0.0
        # excludes reserved space >= 224.0.0.0
        # excludes network & broadcast addresses
        # (first & last IP address of each class)
        + r"(?:[1-9]\d?|1\d\d|2[01]\d|22[0-3])" + r"(?:\.(?:1?\d{1,2}|2[0-4]\d|25[0-5])){2}" +
        r"(?:\.(?:[1-9]\d?|1\d\d|2[0-4]\d|25[0-4]))" + r"|"
        # host name
        + r"(?:(?:[a-z\u00a1-\uffff0-9]-?)*[a-z\u00a1-\uffff0-9]+)"
        # domain name
        + r"(?:\.(?:[a-z\u00a1-\uffff0-9]-?)*[a-z\u00a1-\uffff0-9]+)*"
        # TLD identifier
        + r"(?:\.(?:[a-z\u00a1-\uffff]{2,}))" + r")"
        # port number
        + r"(?::\d{2,5})?"
        # resource path
        + r"(?:/\S*)?"
    )

    # CSS_REGEX = r'(\w+)?(\s*>\s*)?(#\w+)?\s*(\.\w+)?(\s*,\s*(\w+)?(\s*>\s*)?(#\w+)?\s*(\.\w+)?)*\s*\{\s*(\s*[\w\-_]+\s*:\s*[^;]+?\s*;)*\s*\}'

    CLEANUP = re.compile(
        r'|'.join([METADATA_FRIENDS_REGEX, SIGNATURE_REGEX, URL_REGEX]  # , CSS_REGEX]
                 ),
        re.UNICODE | re.IGNORECASE | re.MULTILINE
    )
    return CLEANUP


_CLEANUP_PATTERN = _compile_cleanup_pattern()
_EMPTY_STRING_PATTERN = re.compile(r'^[\s\.,\?\\\/<>\(\)\+=_`~!@#\$%^&\*\[\]\{\}\|\'";:\-]*$')


def clean_and_parse_description(desc):
    """
    Cleans description and parses out metadata dictionary

    Arguments:
        desc {str} -- Support Ticket description

    Returns:
        (str, dict) -- Tuple of cleaned description and metadata dictionary
    """

    # first parse and cut out metadata, then cleanup rest of description for
    cutDesc, mdict = parse_metadata(desc + '\n')
    return _EMPTY_STRING_PATTERN.sub('', _CLEANUP_PATTERN.sub('', cutDesc.strip())), mdict
