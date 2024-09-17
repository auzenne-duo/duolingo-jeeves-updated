from typing import Any, Dict, Optional, Union

from duolingo_base.dal.auth_api import SearchKeys
from duolingo_base.registry import inject

from jeeves.dal.auth_dal import AuthDAL
from jeeves.util.error_util import print_request_exception


@inject.bind(
    auth_dal=inject.reference(AuthDAL),
)
class UserSearchManager:
    """
    Manager for searching for a user model.
    """

    def __init__(self, auth_dal: AuthDAL):
        self.auth_dal = auth_dal

    def get_user(self, query: Union[str, int]) -> Optional[Dict[str, Any]]:
        """
        Returns the user model corresponding to the query (numeric user id,
        email, or username), or None if the query doesn't match a user when
        interpreted as any of these fields.
        """
        # Search fails if a username/email is used as a user ID, so treat it separately
        search_query = SearchKeys(
            user_id=[query] if isinstance(query, int) or query.isdigit() else [],
            username=[query],
            email=[query],
        )

        # The API call may result in exceptions; suppressing them and logging to Sentry
        try:
            search_result = self.auth_dal.auth_api.search(
                search_query,
                fields=[
                    "user_id",
                    "username",
                    "email",
                    "facebook_id",
                    "google_id",
                    "groups",
                    "phone_number",
                    "wechat_open_id",
                ],
            )
            if search_result:
                return search_result[0]
            else:
                return None
        except Exception as e:
            print_request_exception(e, rollbar_level="warning")
            return None
