import os

from duolingo_base.dal.auth_api import AuthAPI, AuthCredentials


class AuthDAL:
    """
    DAL for exposing the AuthAPI for other clients.
    """

    def __init__(self):
        if os.environ.get("DUOLINGO_JWT"):
            credentials = {"jwt": os.environ.get("DUOLINGO_JWT")}
        else:
            credentials = {
                "username": os.environ.get("DUOLINGO_USERNAME"),
                "password": os.environ.get("DUOLINGO_PASSWORD"),
            }

        self._auth_api = AuthAPI(
            auth_host="https://auth.duolingo.com",
            credentials=AuthCredentials(**credentials),
        )

    @property
    def auth_api(self) -> AuthAPI:
        """
        Returns AuthAPI
        """
        return self._auth_api

    @property
    def beta_user_security_roles(self) -> str:
        """
        Returns security roles for the beta user.
        """
        return "ios-builds-download"
