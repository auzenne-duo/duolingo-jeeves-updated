#!/usr/bin/env python2
import json
from itertools import imap
from glob import glob
import operator

from jeeves.model.support_ticket import SupportTicket

class AbstractSupportTicketDAL(object):
    def get_support_tickets(self):
        pass

    @staticmethod
    def support_ticket_maker(category_label_func):
        def factory(ticket_json):
            return SupportTicket(
                ticket_id=ticket_json['id'],
                date_time=ticket_json['created_at'],
                subject=ticket_json['subject'],
                description=ticket_json['description'],
                category_labels=category_label_func(ticket_json)
            )
        return factory

class AbstractFileSystemSupportTicketDAL(AbstractSupportTicketDAL):

    def _ticket_generator(self, factory):
        pass

    def _category_label_func(self, ticket_json):
        pass

    def get_support_tickets(self):
        return self._ticket_generator(self.support_ticket_maker(self._category_label_func))

class FileSystemSupportTicketDAL(AbstractFileSystemSupportTicketDAL):

    _file = 'data/category_dataset-en.txt'
    _category_label_func = staticmethod(operator.itemgetter('category_labels'))

    def _ticket_generator(self, factory):
        with open(self._file, 'r') as input_file:
            for ticket_json in imap(json.loads, input_file):
                yield factory(ticket_json)

class ZendeskFileSystemSupportTicketDAL(AbstractFileSystemSupportTicketDAL):

    _category_label_func = staticmethod(lambda tk: ['bug'])

    def __init__(self, directory):
        super(ZendeskFileSystemSupportTicketDAL, self).__init__()
        self._files = glob(directory + '/tickets_*.json')

    def _ticket_generator(self, factory):
        for fileName in self._files:
            with open(fileName, 'r') as input_file:
                for ticket_json in json.load(input_file)['tickets']:
                    yield factory(ticket_json)


SupportTicketDAL = FileSystemSupportTicketDAL()
