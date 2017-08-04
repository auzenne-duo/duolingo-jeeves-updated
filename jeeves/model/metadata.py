from collections import namedtuple
import json

from jeeves.dal.config.metadata import FIELD_TITLES
from jeeves.model import JeevesObject

class Metadata(
    JeevesObject,
    namedtuple('MD', FIELD_TITLES)
):
    """Metadata container"""

    __slots__ = ()

    def __new__(cls, metadata_dict):
        # CONSIDER: Will currently ignore keys in `metadata_dict` that aren't
        # part of FIELD_TITLES. This is silent, but maybe performs faster?
        # Might want to be not silent about this deletion.
        d = {field: metadata_dict.get(field, '') for field in cls._fields}
        return super().__new__(cls, **d)

    def __serialize__(self):
        return self._asdict()

    def keys(self):
        return self._fields

    def values(self):
        return self.__iter__()

    def items(self):
        return zip(self.keys(), self.values())

    def __bool__(self):
        return any(self)

    @classmethod
    def from_string(cls, s):
        try:
            o = json.loads(s)
        except json.decoder.JSONDecodeError:
            print(s)
            o = {}
        return cls(o)
