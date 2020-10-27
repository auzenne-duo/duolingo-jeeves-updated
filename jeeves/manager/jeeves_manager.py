"""
Abstract parent for all other manager classes.
A manager controls a class of documents, in particular, it contains functionality
to download such documents from an external source.
"""


from abc import ABC, abstractmethod
from typing import Any, Iterator, List, Type

from jeeves.model.jeeves_document import JeevesDocument


class JeevesManager(ABC):
    @classmethod
    def get_all_managers(cls) -> List[Type["JeevesManager"]]:
        """
        Essentially a wrapper function to avoid reflection logic suddenly
        appearing where it isn't expected.

        Parameters: None

        Returns:
            A list of all subclasses of JeevesManager, i.e. all the document
            managers we currently have.
        """
        return cls.__subclasses__()

    @staticmethod
    @abstractmethod
    def get_managed_document_type() -> JeevesDocument:
        """
        Return the class corresponding to the type of documents manged by this class

        Parameters: None

        Returns:
            A subclass of JeevesDocument
        """
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def download_documents(start_timestamp: Any) -> Iterator[JeevesDocument]:
        """
        Downloads documents from an external source and yields them.
        The external source specified in this method in subclasses of this class
        should logically match that subclass, i.e., a subclass of this class
        called XYZDocument should download tickets from XYZ source.

        Parameters:
            start_timestamp: Some kind of timestamp to indicate which documents
                             should be downloaded. Generally, all documents
                             after this timestamp will be downloaded.

            TODO: REPLACE ABOVE PARAMETER WITH SOMETHING MORE INFORMATIVE
                  TO FACILITATE A BETTER CHECKPOINTING SYSTEM

        Yields:
            Documents with timestamps later than the given timestamp.
        """
        raise NotImplementedError
