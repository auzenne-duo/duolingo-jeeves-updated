"""
A set of languages supported in this project.
"""

from enum import Enum, auto


class SUPPORTED_LANGUAGES(Enum):
    """Duolingo Jeeves supported languages"""

    en = auto()  # English
    es = auto()  # Spanish
    de = auto()  # German
    fr = auto()  # French
    it = auto()  # Italian
    ja = auto()  # Japanese
    ru = auto()  # Russian
    zh = auto()  # Chinese

    xx = auto()  # Other

    @classmethod
    def get_misc_language_name(cls) -> str:
        """
        Returns the name of the "other" language category. Remember kids, magic
        numbers are bad!

        Note: This would be a private method since it isn't used outside this
        class, but apparently Enum classes in Python reserve all method names
        that start with single underscores so I can't give it a private name.
        """
        return cls.xx.name

    @classmethod
    def filter_misc_languages(cls, lang: str) -> str:
        """
        Checks if a language is in our set of supported languages. If it is,
        return the value of lang. Otherwise, return the value of the "other"
        language category.

        Parameters:
            lang: A language that we may wish to categorize as "other".

        Returns:
            The provided value of `lang` if that value is a supported language,
            otherwise the name of the "other" language category.
        """

        if lang in cls.__members__:
            return lang
        return cls.get_misc_language_name()
