from collections import namedtuple

from jeeves.dal.config.metadata import FIELD_TITLES
from jeeves.model import JeevesObject

class Metadata(
    JeevesObject,
    namedtuple('MD', FIELD_TITLES)
):
    """Metadata container"""

    __slots__ = ()

    def __new__(cls, metadata_dict):
        d = metadata_dict.copy()
        for field in cls._fields:
            d.setdefault(field, '')
        return super().__new__(cls, **d)

    def __serialize__(self):
        return self._asdict()
