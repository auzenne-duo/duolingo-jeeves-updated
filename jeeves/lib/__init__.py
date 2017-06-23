import re

import langid

def langClassify(text):
    return langid.classify(text)[0]

descriptionMetadata = re.compile(r'-{3,}\s+App information:[\s\S]+?-{3,}|(?:[A-z ]+:.*)(?:\n[A-z ]+:.*)+|[A-z]+\.txt|(?:Sent from|Enviado desde) .*')
URL_REGEX = re.compile(
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
    , re.UNICODE)


def clean_description(desc):
    return URL_REGEX.sub('', descriptionMetadata.sub('', desc))
