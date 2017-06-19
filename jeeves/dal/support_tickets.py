import simplejson as json

from jeeves.model.support_ticket import SupportTicket

class AbstractSupportTicketDAL(object):
    def get_support_tickets(self):
        pass

class FileSystemSupportTicketDAL(AbstractSupportTicketDAL):

    _file = 'data/category_dataset.txt'

    def get_support_tickets(self):
        support_tickets = []
        with open(self._file, 'r') as input_file:
            for line in input_file:
                ticket_json = json.loads(line)
                ticket = SupportTicket(ticket_json['id'],
                                       ticket_json['subject'],
                                       ticket_json['description'],
                                       category_labels=ticket_json['category_labels'])
                support_tickets.append(ticket)
        return support_tickets


SupportTicketDAL = FileSystemSupportTicketDAL()
