"""
Mapping from data source identifiers to document classes.
This had to be split off from the main JeevesDocument class
to avoid problems with recursive import statements.
"""

from jeeves.model.zendesk_document import ZendeskDocument


IDENTIFIER_DOCUMENT_MAPPING = {ZendeskDocument.get_data_source_identifier(): ZendeskDocument}
