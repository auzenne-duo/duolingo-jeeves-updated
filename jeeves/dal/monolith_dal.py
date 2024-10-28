import os
from typing import Optional
from urllib.parse import urljoin

import requests

from jeeves.util.error_util import print_request_exception

DUOLINGO_JWT = os.getenv("DUOLINGO_JWT")
DEFAULT_BASE_URL = "https://api.duolingo.com/2017-06-30/"


class MonolithDAL:
    def __init__(self):
        self._headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {DUOLINGO_JWT}",
            "User-Agent": "product-quality (DuolingoService)",
        }

    def get_user_id_by_email_or_username(
        self, email: Optional[str] = None, username: Optional[str] = None
    ) -> int:
        """Get a user ID based on their email or username.
        Arguments:
            email (Optional[str]): User's email address (default: None)
            username (Optional[str]): User's username (default: None)
        """
        assert bool(email is not None) != bool(
            username is not None
        ), "Must provide either email or username, but not both."

        if email is not None:
            params = {"email": email}
        elif username is not None:
            params = {"username": username}
        else:
            assert False, "Email and username are both None."

        # Search for user
        full_url = urljoin(DEFAULT_BASE_URL, "users")
        try:
            response = requests.get(full_url, params=params, headers=self._headers)
            response.raise_for_status()
        except Exception as e:
            print_request_exception(e, rollbar_level="warning")
            return None

        # Parse user ID from response
        users = response.json()["users"]
        if len(users) == 1:
            return users[0]["id"]
        return None
