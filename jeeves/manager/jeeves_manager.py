"""
Abstract parent for all other manager classes.
A manager controls a class of documents, in particular, it contains functionality
to download such documents from an external source.
"""


from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Type

from duolingo_base.dal.s3 import S3Client

from jeeves.model.custom_types import JSON
from jeeves.model.jeeves_document import JeevesDocument

_DEFAULT_CHECKPOINTING_THRESHOLD = 1000


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
    def get_checkpoint_file_name() -> str:
        """
        Returns the name of the S3 file used for storing checkpoint data.
        """
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def update_s3_if_necessary(
        s3_client: S3Client, bucket_name: str, default_start_timestamp: float
    ) -> None:
        """
        Downloads documents from an external source and stores them to S3.
        The external source specified in this method in subclasses of this class
        should logically match that subclass, i.e., a subclass of this class
        called XYZDocument should download tickets from XYZ source.

        Parameters:
            s3_client: Duolingo base library S3 DAL object. Expected to have
                       read/write access to a bucket with name bucket_name.
            bucket_name: The name of the S3 bucket we should store documents to.
            default_start_timestamp: Some kind of timestamp to indicate which
                                     documents should be downloaded. Generally,
                                     all documents after this timestamp will be
                                     downloaded.

            TODO: REPLACE ABOVE PARAMETER WITH SOMETHING MORE INFORMATIVE
                  TO FACILITATE A BETTER CHECKPOINTING SYSTEM

        """
        raise NotImplementedError

    @staticmethod
    def get_checkpointing_threshold() -> int:
        """
        Returns how many documents of this type should be downloaded before
        storing them in Elasticsearch via checkpointing. This number is somewhat
        arbitrary and is influenced by the speed at which documents are downloaded.

        Parameters: None

        Returns:
            An integer, representing the number of documents that should be
            collected before storing them in a checkpoint.
        """
        return _DEFAULT_CHECKPOINTING_THRESHOLD

    @staticmethod
    @abstractmethod
    def get_most_recent_s3_populated_date(s3_client: S3Client, bucket_name: str) -> datetime:
        """
        Returns the most recent date for which this manager has data populated
        in the S3 bucket indicated by the provided client and bucket name.

        Parameters:
            s3_client: Duolingo base library S3 DAL object. Expected to have
                       read access to a bucket with name bucket_name.
            bucket_name: The name of the S3 bucket we want to investigate.

        Returns:
            A datetime.datetime object representing the most recent date for
            which this manager has data populated.
        """
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def process_document(doc_json: JSON) -> Optional[Type["JeevesDocument"]]:
        """
        Convert JSON (representing a document) downloaded from an external
        source into a JeevesDocument representation of that document.
        The process by which this conversion happens depends on the type of
        document being converted, but must at least include some verification
        that the document is a valid candidate for indexing. If the document
        fails this verification process, instead return None.

        Parameters:
            doc_json: JSON downloaded from an external source, representing a
                      document to be processed.

        Returns:
            A JeevesDocument representation of the provided JSON document, or
            None if the document was invalid.
        """
        raise NotImplementedError
