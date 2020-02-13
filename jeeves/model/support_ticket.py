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
    ):
        """
        Parameters:
            ticket_id (int): A zendesk ticket ID.
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
        """
        # More meta data can be fetched using this ID.
        if category_labels is None:
            category_labels = []
        if metadata is None:
            metadata = {}
        metadata = Metadata(metadata)
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
        )

    def __repr__(self):
        def summarize(item):
            key, value = item
            if key == "description" and len(value) > 30:
                return (key, value.replace("\n", " ")[:30] + "...")
            else:
                return item

        variables = ", ".join("%s=%s" % summarize(item) for item in self._asdict().items())
        return "%s(%s)" % (type(self).__name__, variables)

    def __serialize__(self):
        return self._asdict()
