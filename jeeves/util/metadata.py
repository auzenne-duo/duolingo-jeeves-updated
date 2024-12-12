import operator
import re
from typing import Any, Tuple

from jeeves.dal.config.metadata import Config


def parse(parseFormat):
    def parseInner(pField):
        line = parseFormat.format(
            **{
                k: re.escape(v) if k != "pattern" and isinstance(v, str) else v
                for k, v in pField.items()
            }
        )
        if pField["optional"]:
            line = rf"(?:{line})?"
        return line

    return parseInner


_METADATA_CFG = Config["metadata"]

_MDATA_REGEXES = {
    plat: re.compile("".join(map(parse(platData["parseFormat"]), platData["parseFields"])))
    for plat, platData in _METADATA_CFG.items()
}


def parse_metadata(txt: str) -> Tuple[str, Any]:
    """
    Cuts and parses plaintext metadata out of string

    Arguments:
        txt {str} -- Input string to be cut/parsed

    Returns:
        (str, dict) -- Tuple of txt with metadata cut out and metadata as dictionary
    """

    def getRawMetadataDict():
        for plat, mdataParser in _MDATA_REGEXES.items():
            match = mdataParser.search(txt)
            if match:
                d = match.groupdict()
                for implFields in _METADATA_CFG[plat]["implicitFields"]:
                    fld, val = operator.itemgetter("field", "value")(implFields)
                    d[fld] = val
                return match.span(), d
        # if none of the parsers find metadata
        return (0, 0), {}

    # TODO: Post-process the metadata dictionaries by platform to
    # - enforce datatype conversions
    # - apply normalization rules by platform
    (s, t), mdict = getRawMetadataDict()
    return (txt[:s] + txt[t:]), mdict
