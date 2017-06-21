import json
from itertools import imap

from jeeves.model.support_ticket import SupportTicket

class AbstractSupportTicketDAL(object):
    def get_labeled_support_tickets(self, language='en'):
        """ Get a list of SupportTickets with category_labels annotated. """
        pass

    def get_sample_support_tickets(self):
        """ Get a list of 1000 sample SupportTickets to be shown for prototyping the system. """
        pass


class FileSystemSupportTicketDAL(AbstractSupportTicketDAL):

    _labeled_ticket_file = 'data/category_dataset-%s.txt'
    _sample_ticket_file = 'data/sample_tickets.json'

    @staticmethod
    def _deserialize_json(ticket_json):
        return SupportTicket(
                    ticket_id=ticket_json['id'],
                    date_time=ticket_json['created_at'],
                    subject=ticket_json['subject'],
                    description=ticket_json['description'],
                    category_labels=ticket_json.get('category_labels')
                )

    def get_labeled_support_tickets(self, language='en'):
        with open(self._labeled_ticket_file % language, 'r') as input_file:
            return [
                self._deserialize_json(ticket_json)
                for ticket_json in imap(json.loads, input_file)
            ]

    def get_sample_support_tickets(self):
        with open(self._sample_ticket_file, 'r') as input_file:
            return [
                self._deserialize_json(ticket_json)
                for ticket_json in json.load(input_file)['tickets']
            ]

SupportTicketDAL = FileSystemSupportTicketDAL()
