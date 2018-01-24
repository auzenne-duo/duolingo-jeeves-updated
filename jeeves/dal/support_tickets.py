"""
DAL for zendesk support ticket dataset.
"""
from abc import ABCMeta, abstractmethod
import contextlib
import functools
from glob import glob
import gzip
import os
import re
import simplejson as json
from tqdm import tqdm

from jeeves import data_directory
from jeeves.dal.category_annotations import CategoryAnnotationDAL
from jeeves.exception.model import UnsupportedLanguageError
from jeeves.lib.file_io import read_from_file, write_to_file
from jeeves.model.products import Products
from jeeves.model.support_ticket import SupportTicket
from jeeves.model.supported_languages import SUPPORTED_LANGUAGES
from jeeves.util.classify import detect_language, detect_product
from jeeves.util.cleanup import clean_and_parse_description
from jeeves.util.json_encoder import JeevesJSONEncoder
from jeeves.util.s3 import S3, S3_SEGMENTED_DIR, S3_BUCKET_ID


_TICKET_FILE_TEMPLATE = 'tickets-{lang}-{prod}.txt.gz'

_TICKET_FILE_REGEX = re.compile(r'tickets_(\d+)\.json(\.gz)?$')


def extract_ticket_timestamp(filename):
    return int(_TICKET_FILE_REGEX.search(filename).group(1))


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
            ticket_id=ticket_json['ticket_id'],
            date_time=ticket_json['date_time'],
            subject=ticket_json['subject'],
            description=ticket_json['description'],
            category_labels=CategoryAnnotationDAL.get_annotations(ticket_json['ticket_id']),
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

    _labeled_ticket_file = _TICKET_FILE_TEMPLATE

    def __init__(self, ticket_file=None):
        if ticket_file is not None:
            self._labeled_ticket_file = ticket_file

    def get_labeled_support_tickets(self, language=SUPPORTED_LANGUAGES.en, product=Products.LA):
        file_name = self._labeled_ticket_file.format(lang=language.name, prod=product.name)
        input_file = read_from_file(file_name + '.gz', dir_path=data_directory)

        yield from map(self._deserialize_json, map(json.loads, input_file))


class ZendeskFileSystemSupportTicketDAL(AbstractFileSystemSupportTicketDAL):

    _zendesk_ticket_dir = os.path.join(data_directory, 'zendesk')

    def __init__(self):
        super(ZendeskFileSystemSupportTicketDAL, self).__init__()
        self._files = sorted(glob(os.path.join(self._zendesk_ticket_dir, 'tickets_*.json.gz')),
                             key=extract_ticket_timestamp)

    def get_labeled_support_tickets(self, language=SUPPORTED_LANGUAGES.en, product=Products.LA):
        for file_name in self._files:
            input_file = read_from_file(os.path.basename(file_name),  # Already has .gz
                                        dir_path=self._zendesk_ticket_dir)

            for ticket_json in json.loads(input_file)['tickets']:
                ticket = self._deserialize_json(ticket_json)
                try:
                    discoveredLang = detect_language(ticket.description)
                except UnsupportedLanguageError:
                    pass
                else:
                    if discoveredLang == language:
                        yield ticket

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
        customJSONDump = functools.partial(json.dumps, cls=JeevesJSONEncoder)
        # create a `with` context manager for a programmatically defined number of (output) files
        with contextlib.ExitStack() as stack:
            # create a segmented out file for all supported languages and platforms
            out_files = {
                (lang, prod):
                gzip.open(os.path.join(data_directory,
                                       _TICKET_FILE_TEMPLATE.format(lang=lang.name, prod=prod.name)), 'wb')
                for lang in SUPPORTED_LANGUAGES
                for prod in Products
            }
            for mgr in out_files.values():
                # __enter__ the with context, and register it to be __exit__'ed
                stack.enter_context(mgr)

            id_history = set()
            # now go through each input ticket file
            for filename in tqdm(self._files, desc='Segmenting Zendesk Tix'):
                input_file = read_from_file(os.path.basename(filename),  # Already has .gz
                                            dir_path=self._zendesk_ticket_dir)
                for ticket_json in json.loads(input_file)['tickets']:
                    ticket = self._deserialize_json(ticket_json)
                    # done in this order because ticket creation filters out
                    # some junk from the messages (urls, metadata, etc.)

                    if ticket.ticket_id in id_history:
                        continue
                    id_history.add(ticket.ticket_id)

                    # Skip tickets that have an empty string ('') description
                    # after cleanup, which are those that consist of just
                    # punctuation/spacing after cleanup
                    if not ticket.description:
                        continue
                    try:
                        language = detect_language(ticket.description)
                    except UnsupportedLanguageError:
                        # ignore tickets in unsupported languages
                        pass
                    # `classifyProd` requires access to `subject` and `tags`
                    else:
                        prod = detect_product(ticket_json)
                        if (language, prod) in out_files:
                            out_files[language, prod].write(customJSONDump(ticket).encode('utf-8'))
        return list(map(lambda f: f.name, out_files.values()))


class S3RemoteSupportTicketDAL(FileSystemSupportTicketDAL, AbstractRemoteSupportTicketDAL):

    def __init__(self, ticket_file=None):
        self._init = False
        super().__init__(ticket_file=ticket_file)

    def lazy_init(self):
        segmented_files = list(S3.yield_filenames(S3_BUCKET_ID, path_prefix=S3_SEGMENTED_DIR))
        for file_path in tqdm(segmented_files, desc='Downloading Segmented Files'):
            file_name = os.path.basename(file_path)
            ticket_json = S3.download(S3_BUCKET_ID, os.path.join(S3_SEGMENTED_DIR, file_name))
            write_to_file(ticket_json + '.gz', file_name)
        self._init = True

    def get_labeled_support_tickets(self, language=SUPPORTED_LANGUAGES.en, product=Products.LA):
        if not self._init:
            self.lazy_init()
        yield from super().get_labeled_support_tickets(language, product)


SupportTicketDAL = S3RemoteSupportTicketDAL()
