import simplejson as json
from itertools import imap

from jeeves.model.support_ticket import SupportTicket

class AbstractSupportTicketDAL(object):
    def get_support_tickets(self):
        pass

class FileSystemSupportTicketDAL(AbstractSupportTicketDAL):

    _file = 'jeeves/data/category_dataset-en.txt'

    def get_support_tickets(self):
        with open(self._file, 'r') as input_file:
            return [
                SupportTicket(
                    ticket_json['id'],
                    ticket_json['subject'],
                    ticket_json['description'],
                    category_labels=ticket_json['category_labels']
                )
                for ticket_json in imap(json.loads, input_file)
            ]


SupportTicketDAL = FileSystemSupportTicketDAL()
