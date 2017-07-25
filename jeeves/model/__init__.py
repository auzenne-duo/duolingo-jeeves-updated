from abc import ABCMeta, abstractmethod


class JeevesObject(object, metaclass=ABCMeta):
    """Base object for all custom data structures in Jeeves"""

    @abstractmethod
    def __serialize__(self):
        return self.__dict__

    def subserialize(self, *fields):
        d = self.__serialize__()
        return {fld: d[fld] for fld in fields}
