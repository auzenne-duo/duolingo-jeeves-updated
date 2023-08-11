"""
Mapping from data source identifiers to document manager classes.
This is a class instead of a dict of tuples as this lets us avoid magic indices.
"""

from typing import List, Optional, Type

from jeeves.manager.appfigures_manager import AppfiguresManager
from jeeves.manager.jeeves_manager import JeevesManager
from jeeves.manager.jira_manager import JiraManager
from jeeves.manager.reddit_manager import RedditManager
from jeeves.manager.zendesk_manager import ZendeskManager


class IdentifierManagerMapping:
    def __init__(self) -> None:
        self._ident_doc_map = {
            JiraManager.get_managed_document_type().get_data_source_identifier(): JiraManager,
            ZendeskManager.get_managed_document_type().get_data_source_identifier(): ZendeskManager,
            AppfiguresManager.get_managed_document_type().get_data_source_identifier(): AppfiguresManager,
            RedditManager.get_managed_document_type().get_data_source_identifier(): RedditManager,
        }

    def get_manager_for_identifier(self, identifier: str) -> Optional[Type[JeevesManager]]:
        """
        Looks up the manager for a particular identifier. Returns None for
        unrecognized identifiers.

        Parameters:
            identifier: The identifier for which you wish to find a manager.

        Returns:
            The manager for the provided identifier, or None if the identifier
            is not present in the mapping.
        """
        return self._ident_doc_map.get(identifier, None)

    def get_all_managers(self) -> List[Type[JeevesManager]]:
        """
        Gets all known document managers as a list.

        Returns:
            A list of all document managers that Jeeves is aware of.
        """
        return self._ident_doc_map.values()


IDManagerMap = IdentifierManagerMapping()
