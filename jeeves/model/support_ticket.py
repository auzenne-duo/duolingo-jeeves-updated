"""
A model representing a support ticket.
"""

from collections import namedtuple

from jeeves.model import JeevesObject
from jeeves.model.metadata import Metadata

_TICKET_FIELDS = (
    "ticket_id",
    "date_time",
    "subject",
    "description",
    "language",
    "product",
    "priority",
    "via",
    "tags",
    "requester_id",
    "category_labels",
    "metadata",
    "data_source",
)


class SupportTicket(JeevesObject, namedtuple("ST", " ".join(_TICKET_FIELDS))):

    __slots__ = ()

    def __new__(
        cls,
        ticket_id,
        date_time,
        subject,
        description,
        language,
        product,
        priority,
        via,
        tags,
        requester_id,
        category_labels=None,
        metadata=None,
        data_source=None,
    ):
        """
        Parameters:
            ticket_id (str): A zendesk ticket ID.
            date_time (datetime.datetime): A UTC datetime at which the ticket was created.
            subject (str): A subject of the ticket.
            description (str): A description of the ticket. This may include unstructured meta data.
            language (str): A ticket language automatically identified by langid module.
            product (str): A Duolingo product label (See jeeves.model.products).
            priority: A priority of an issue (urgent, high, normal, or low).
            via: An object explaining how the ticket was created.
            tags (list<str>): A list of tags assigned on Zendesk.
            requester_id: An ID of zendesk user who requested this ticket.
            category_labels (collection<str>): Gold standard labeled assigned by human annotator.
            metadata (dict): Metadata dictionary parsed out of Zendesk descriptions.
            tokens (list<str>): A full list of 'words' in the ticket's subject and description.
            data_source (str): The name of the service where we obtained this ticket.
        """
        # More meta data can be fetched using this ID.
        if category_labels is None:
            category_labels = []
        if metadata is None:
            metadata = {}
        metadata = Metadata(metadata)
        if data_source is None:
            data_source = ""
        return super().__new__(
            cls,
            ticket_id,
            date_time,
            subject,
            description,
            language,
            product,
            priority,
            via,
            tags,
            requester_id,
            category_labels,
            metadata,
            data_source,
        )

    def __repr__(self):
        def summarize(item):
            key, value = item
            if key == "description" and len(value) > 30:
                return (key, value.replace("\n", " ")[:30] + "...")
            else:
                return item

        def stringify_summary(sum_key, sum_val):
            return f"{sum_key}={sum_val}"

        variables = ", ".join(
            stringify_summary(*(summarize(item))) for item in self._asdict().items()
        )
        return f"{type(self).__name__}({variables})"

    def __serialize__(self):
        return self._asdict()
