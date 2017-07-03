from jeeves.exception import JeevesException

class UnsupportedLanguageError(JeevesException, KeyError):
    """ KeyError-like exception for unsupported languages """
