import json
from glob import glob
import os

from jeeves import data_directory
from jeeves.lib import clean_description
from jeeves.lib import langClassify
from jeeves.model.support_ticket import SupportTicket

class AbstractSupportTicketDAL(object):
    def get_labeled_support_tickets(self, language='en'):
        """ Get a list of SupportTickets with category_labels annotated. """
        pass

    @staticmethod
    def _deserialize_json(ticket_json):
        return SupportTicket(
            ticket_id=ticket_json['id'],
            date_time=ticket_json['created_at'],
            subject=ticket_json['subject'],
            description=clean_description(ticket_json['description']),
            category_labels=ticket_json.get('category_labels', list())
        )

    def get_sample_support_tickets(self):
        """ Get a list of 1000 sample SupportTickets to be shown for prototyping the system. """
        pass

class AbstractFileSystemSupportTicketDAL(AbstractSupportTicketDAL):

    _sample_ticket_file = 'data/sample_tickets.json'

    def get_sample_support_tickets(self):
        with open(self._sample_ticket_file, 'r') as input_file:
            return [
                self._deserialize_json(ticket_json)
                for ticket_json in json.load(input_file)['tickets']
            ]

class FileSystemSupportTicketDAL(AbstractFileSystemSupportTicketDAL):

    _labeled_ticket_file = os.path.join(data_directory, 'category_dataset-en.txt')

    def __init__(self, ticket_file=None):
        if ticket_file is not None:
            self._labeled_ticket_file = os.path.join(data_directory, ticket_file)

    def get_labeled_support_tickets(self, language='en'):
        with open(self._labeled_ticket_file.format(language), 'r') as input_file:
            yield from map(self._deserialize_json, map(json.loads, input_file))

class ZendeskFileSystemSupportTicketDAL(AbstractFileSystemSupportTicketDAL):

    _zendesk_ticket_dir = os.path.join(data_directory, 'zendesk')

    def __init__(self):
        super(ZendeskFileSystemSupportTicketDAL, self).__init__()
        self._files = glob(os.path.join(self._zendesk_ticket_dir, 'tickets_*.json'))

    def get_labeled_support_tickets(self, language='en'):
        for fileName in self._files:
            with open(fileName, 'r') as input_file:
                for ticket_json in json.load(input_file)['tickets']:
                    supTik = self._deserialize_json(ticket_json)
                    if langClassify(supTik.description) == language:
                        yield supTik

SupportTicketDAL = FileSystemSupportTicketDAL()
