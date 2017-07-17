"""
DAL for zendesk support ticket dataset.
"""
from abc import ABCMeta, abstractmethod
import contextlib
from glob import glob
import json
import os
import re
import sys

from jeeves import data_directory
from jeeves.dal.category_annotations import CategoryAnnotationDAL
from jeeves.exception.model import UnsupportedLanguageError
from jeeves.util.cleanup import clean_and_parse_description
from jeeves.model.products import Products
from jeeves.model.support_ticket import SupportTicket
from jeeves.model.supported_languages import SUPPORTED_LANGUAGES
from jeeves.util.classify import classifyLang, classifyProd
from jeeves.util.s3 import S3, S3_SEGMENTED_DIR, S3_BUCKET_ID


_TICKET_FILE_TEMPLATE = 'tickets-{lang}-{prod}.txt'


class AbstractSupportTicketDAL(object, metaclass=ABCMeta):
    @abstractmethod
    def get_labeled_support_tickets(self, language=SUPPORTED_LANGUAGES.en, product=Products.LA):
        """
        Get a list of SupportTickets with category_labels annotated.

        Keyword Arguments:
            language {SUPPORTED_LANGUAGES} -- lang id of tickets to fetch
                                              (default: {SUPPORTED_LANGUAGES.en})
            product {Products} -- product whose tickets to retreive (default: {Products.LA})
        """

    @staticmethod
    def _deserialize_json(ticket_json):
        return SupportTicket(
            ticket_id=ticket_json['id'],
            date_time=ticket_json['created_at'],
            subject=ticket_json['subject'],
            description=ticket_json['description'],
            category_labels=CategoryAnnotationDAL.get_annotations(ticket_json['id']),
            metadata=ticket_json.get('metadata', {})
        )

class AbstractFileSystemSupportTicketDAL(AbstractSupportTicketDAL):
    @abstractmethod
    def get_labeled_support_tickets(self, language=SUPPORTED_LANGUAGES.en, product=Products.LA):
        pass

class AbstractRemoteSupportTicketDAL(AbstractSupportTicketDAL):
    """ Abstract Base class for tickets fetched or accessed non-locally"""
    @abstractmethod
    def get_labeled_support_tickets(self, language=SUPPORTED_LANGUAGES.en, product=Products.LA):
        pass

class FileSystemSupportTicketDAL(AbstractFileSystemSupportTicketDAL):

    _labeled_ticket_file = os.path.join(data_directory, _TICKET_FILE_TEMPLATE)

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
        TICKET_FILE_REGEX = re.compile(r'tickets_(\d+)\.json$')
        self._files = sorted(glob(os.path.join(self._zendesk_ticket_dir, 'tickets_*.json')), key=lambda s: int(TICKET_FILE_REGEX.search(s).group(1)))

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

    @staticmethod
    def _deserialize_json(ticket_json):
        desc, metadata = clean_and_parse_description(ticket_json['description'])
        return SupportTicket(
            ticket_id=ticket_json['id'],
            date_time=ticket_json['created_at'],
            subject=ticket_json['subject'],
            description=desc,
            category_labels=CategoryAnnotationDAL.get_annotations(ticket_json['id']),
            metadata=metadata
        )

    def segment_labeled_support_tickets(self):
        """
        Segment all the Zendesk tickets into separate files for each
        supported language and product
        """
        from tqdm import tqdm
        # create a `with` context manager for a programmatically defined number of (output) files
        with contextlib.ExitStack() as stack:
            # create a segmented out file for all supported languages and platforms
            outFiles = {
                (lang, prod):
                open(
                    os.path.join(
                        data_directory,
                        _TICKET_FILE_TEMPLATE.format(
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
            for fileName in tqdm(self._files, desc='Segmenting Zendesk Tix'):
                with open(fileName, 'r') as input_file:
                    for ticket_json in json.load(input_file)['tickets']:
                        supTik = self._deserialize_json(ticket_json)
                        # done in this order because ticket creation filters out
                        # some junk from the messages (urls, metadata, etc.)

                        # Skip tickets that have an empty string ('') description
                        # after cleanup, which are those that consist of just
                        # punctuation/spacing after cleanup
                        if not supTik.description:
                            continue
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
        return list(map(lambda f: f.name, outFiles.values()))

class S3RemoteSupportTicketDAL(FileSystemSupportTicketDAL, AbstractRemoteSupportTicketDAL):

    def __init__(self, ticket_file=None):
        # First, download from S3
        print('Downloading segmented data files', file=sys.stderr)
        for fPath in S3.yield_filenames(S3_BUCKET_ID, path_prefix=S3_SEGMENTED_DIR):
            fName = os.path.basename(fPath)
            with open(os.path.join(data_directory, fName), 'wb') as f:
                f.write(
                    S3.download(
                        S3_BUCKET_ID,
                        os.path.join(
                            S3_SEGMENTED_DIR,
                            fName
                        )
                    )
                )
        print('Finished downloading segmented data files', file=sys.stderr)
        super().__init__(ticket_file=ticket_file)


SupportTicketDAL = S3RemoteSupportTicketDAL()
