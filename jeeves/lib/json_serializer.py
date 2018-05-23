from dateutil.parser import parse
import functools
import pytz
import simplejson as json

from jeeves.dal.category_annotations import CategoryAnnotationDAL
from jeeves.model.support_ticket import SupportTicket
from jeeves.util.classify import detect_language, detect_product
from jeeves.util.cleanup import clean_and_parse_description
from jeeves.util.json_encoder import JeevesJSONEncoder

_CUSTOM_JSON_DUMP = functools.partial(json.dumps, cls=JeevesJSONEncoder)


def deserialize_zendesk_ticket_json(ticket_json):
    """
    Convert a JSON representation of a ticket returned from Zendesk API to our ticket model.

    Parameters:
        ticket_json (dict): A ticket json.

    Returns:
        A SupportTicket object.
    """
    desc, metadata = clean_and_parse_description(ticket_json['description'])
    return SupportTicket(
        ticket_id=ticket_json['id'],
        date_time=parse(ticket_json['created_at']).astimezone(pytz.utc),
        subject=ticket_json['subject'],
        description=desc,
        language=detect_language(desc),
        product=detect_product(ticket_json['tags'], ticket_json['subject']).name,
        priority=ticket_json['priority'],
        via=ticket_json['via'],
        tags=ticket_json['tags'],
        requester_id=ticket_json['requester_id'],
        category_labels=CategoryAnnotationDAL.get_annotations(ticket_json['id']),
        metadata=metadata
    )


def deserialize_jeeves_ticket_json(ticket_json):
    """
    Convert a JSON representation of a ticket to our ticket model.

    Parameters:
        ticket_json (dict): A ticket json.

    Returns:
        A SupportTicket object.
    """
    return SupportTicket(
        ticket_id=ticket_json['ticket_id'],
        date_time=parse(ticket_json['date_time']).astimezone(pytz.utc),
        subject=ticket_json['subject'],
        description=ticket_json['description'],
        language=ticket_json['language'],
        product=ticket_json['product'],
        priority=ticket_json['priority'],
        via=ticket_json['via'],
        tags=ticket_json['tags'],
        requester_id=ticket_json['requester_id'],
        category_labels=ticket_json['category_labels'],
        metadata=ticket_json['metadata']
    )


def serialize_tickets(tickets):
    """
    Convert a list of tickets into one string where each line is a ticket json.

    Parameters:
        tickets (list<SupportTicket>): A list of tickets.

    Returns:
        A string.
    """
    return '\n'.join(_CUSTOM_JSON_DUMP(ticket) for ticket in tickets)


def deserialize_tickets(json_lines):
    """
    An inverse function of serialize_tickets().

    Parameters:
        json_lines (str): A string where each line is a ticket json.

    Returns:
        List of SupportTicket objects.
    """
    return [deserialize_jeeves_ticket_json(json.loads(line)) for line in json_lines.split('\n')]
