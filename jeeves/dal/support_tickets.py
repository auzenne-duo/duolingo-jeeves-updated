import contextlib
import json
from glob import glob
import os

from jeeves import data_directory
from jeeves.dal.category_annotations import CategoryAnnotationDAL
from jeeves.exception.model import UnsupportedLanguageError
from jeeves.util.cleanup import clean_description
from jeeves.model.products import Products
from jeeves.model.support_ticket import SupportTicket
from jeeves.model.supported_languages import SUPPORTED_LANGUAGES
from jeeves.util.classify import classifyLang, classifyProd

class AbstractSupportTicketDAL(object):
    def get_labeled_support_tickets(self, language=SUPPORTED_LANGUAGES.en, product=Products.LA):
        """
        Get a list of SupportTickets with category_labels annotated.

        Keyword Arguments:
            language {SUPPORTED_LANGUAGES} -- lang id of tickets to fetch
                                              (default: {SUPPORTED_LANGUAGES.en})
            product {Products} -- product whose tickets to retreive (default: {Products.LA})
        """
        pass

    @staticmethod
    def _deserialize_json(ticket_json):
        return SupportTicket(
            ticket_id=ticket_json['id'],
            date_time=ticket_json['created_at'],
            subject=ticket_json['subject'],
            description=clean_description(ticket_json['description']),
            category_labels=CategoryAnnotationDAL.get_annotations(ticket_json['id'])
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

    _labeled_ticket_file = os.path.join(data_directory, 'category_dataset-{lang}.txt')

    def __init__(self, ticket_file=None):
        if ticket_file is not None:
            self._labeled_ticket_file = os.path.join(data_directory, ticket_file)

    def get_labeled_support_tickets(self, language=SUPPORTED_LANGUAGES.en, product=Products.LA):
        with open(self._labeled_ticket_file.format(lang=language.name, prod=product.name), 'r') as input_file:
            yield from map(self._deserialize_json, map(json.loads, input_file))

class ZendeskFileSystemSupportTicketDAL(AbstractFileSystemSupportTicketDAL):

    _zendesk_ticket_dir = os.path.join(data_directory, 'zendesk')

    def __init__(self):
        super(ZendeskFileSystemSupportTicketDAL, self).__init__()
        self._files = glob(os.path.join(self._zendesk_ticket_dir, 'tickets_*.json'))

    def get_labeled_support_tickets(self, language=SUPPORTED_LANGUAGES.en, product=Products.LA):
        for fileName in self._files:
            with open(fileName, 'r') as input_file:
                for ticket_json in json.load(input_file)['tickets']:
                    supTik = self._deserialize_json(ticket_json)
                    try:
                        discoveredLang = classifyLang(supTik.description)
                    except UnsupportedLanguageError:
                        pass
                    else:
                        if discoveredLang == language:
                            yield supTik

    def segment_labeled_support_tickets(self):
        """
        Segment all the Zendesk tickets into separate files for each
        supported language and product
        """
        # create a `with` context manager for a programmatically defined number of (output) files
        with contextlib.ExitStack() as stack:
            # create a segmented out file for all supported languages and platforms
            outFiles = {
                (lang, prod):
                open(
                    os.path.join(
                        data_directory,
                        'tickets-{lang}-{prod}.txt'.format(
                            lang=lang.name,
                            prod=prod.name
                        )
                    ),
                    'w'
                )
                for lang in SUPPORTED_LANGUAGES
                for prod in Products
            }
            for mgr in outFiles.values():
                # __enter__ the with context, and register it to be __exit__'ed
                stack.enter_context(mgr)

            # now go through each input ticket file
            for fileName in self._files:
                with open(fileName, 'r') as input_file:
                    for ticket_json in json.load(input_file)['tickets']:
                        supTik = self._deserialize_json(ticket_json)
                        # done in this order because ticket creation filters out
                        # some junk from the messages (urls, metadata, etc.)
                        try:
                            language = classifyLang(supTik.description)
                        except UnsupportedLanguageError:
                            # ignore tickets in unsupported languages
                            pass
                        # `classifyProd` requires access to `subject` and `tags`
                        else:
                            prod = classifyProd(ticket_json)
                            if (language, prod) in outFiles:
                                print(supTik.__json__(), file=outFiles[language, prod])

SupportTicketDAL = FileSystemSupportTicketDAL()
