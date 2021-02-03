class LanguageCodeMapping:
    def __init__(self):
        self._internal_map = {
            "ENGLISH": "EN",
            "FRENCH": "FR",
            "ARABIC": "AR",
            "GERMAN": "DE",
            "DANISH": "DA",
            "SPANISH": "ES",
            "CHINESE": "ZH-CN",
            "ITALIAN": "IT",
            "PORTUGUESE": "PT",
            "ROMANIAN": "RO",
            "UKRAINIAN": "UK",
            "INDONESIAN": "ID",
            "SCOTTISH GAELIC": "GD",
            "GAELIC": "GD",
            "GUARANÍ": "GN",
            "GUARANI": "GN",
            "SWAHILI": "SW",
            "ESPERANTO": "EO",
            "HIGH VALYRIAN": "HV",
            "VALYRIAN": "HV",
            "POLISH": "PL",
            "HINDI": "HI",
            "IRISH": "GA",
            "GREEK": "EL",
            "KLINGON": "TLH",
            "SWEDISH": "SV",
            "JAPANESE": "JA",
            "HUNGARIAN": "HU",
            "NORWEGIAN": "NO-BO",
            "NORWEGIAN (BOKMÅL)": "NO-BO",
            "DUTCH": "NL-NL",
            "NAVAJO": "NV",
            "CZECH": "CS",
            "WELSH": "CY",
            "RUSSIAN": "RU",
            "CATALAN": "CA",
            "VIETNAMESE": "VI",
            "HEBREW": "HE",
            "KOREAN": "KO",
            "TURKISH": "TR",
            "HAWAIIAN": "HW",
            "LATIN": "LA",
            "FINNISH": "FI",
            "THAI": "TH",
        }

    def code_lookup(self, query: str) -> str:
        if query.upper() in self._internal_map.values():
            return query.upper()
        return self._internal_map.get(query.upper(), "??")


LangCodeMap = LanguageCodeMapping()
