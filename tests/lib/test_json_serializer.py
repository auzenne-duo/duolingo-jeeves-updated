import unittest

from jeeves.lib.json_serializer import (
    deserialize_jeeves_ticket_json,
    deserialize_tickets,
    serialize_tickets,
)
from jeeves.model.metadata import Metadata
from jeeves.util.date_util import datetime_to_str

_TEST_TICKET_JSON = {
    "ticket_id": 123,
    "date_time": "2018-05-01T10:20:35Z",
    "subject": "hello",
    "description": "test",
    "language": "en",
    "product": "LA",
    "priority": "high",
    "via": {},
    "tags": ["tag1", "tag2"],
    "requester_id": "",
    "category_labels": ["cat1", "cat2"],
    "metadata": None,
}


class Test(unittest.TestCase):
    def test_deserialize_ticket(self):
        ticket = deserialize_jeeves_ticket_json(_TEST_TICKET_JSON)
        self.assertEqual(ticket.ticket_id, _TEST_TICKET_JSON["ticket_id"])
        self.assertEqual(datetime_to_str(ticket.date_time), _TEST_TICKET_JSON["date_time"])
        self.assertEqual(ticket.subject, _TEST_TICKET_JSON["subject"])
        self.assertEqual(ticket.language, _TEST_TICKET_JSON["language"])
        self.assertEqual(ticket.product, _TEST_TICKET_JSON["product"])
        self.assertEqual(ticket.priority, _TEST_TICKET_JSON["priority"])
        self.assertEqual(ticket.via, _TEST_TICKET_JSON["via"])
        self.assertEqual(ticket.tags, _TEST_TICKET_JSON["tags"])
        self.assertEqual(ticket.requester_id, _TEST_TICKET_JSON["requester_id"])
        self.assertEqual(ticket.category_labels, _TEST_TICKET_JSON["category_labels"])
        self.assertEqual(type(ticket.metadata), Metadata)

    def test_serialize_and_deserialize(self):
        tickets = [deserialize_jeeves_ticket_json(_TEST_TICKET_JSON)]
        deserialized_tickets = deserialize_tickets(serialize_tickets(tickets))

        # Make sure datetime is timezone-aware and it doesn't change with (de-)serialization.
        self.assertIsNotNone(tickets[0].date_time.tzinfo)
        self.assertIsNotNone(deserialized_tickets[0].date_time.tzinfo)
        self.assertEqual(
            tickets[0].date_time.timestamp(), deserialized_tickets[0].date_time.timestamp()
        )
