from datetime import datetime
from enum import Enum, auto
from typing import Callable, Dict, List, Optional

from elasticsearch_dsl import Search

from jeeves.config.config import COLD_START_DATE
from jeeves.model.jeeves_document import JeevesDocument
from jeeves.model.shake_to_report_category import ShakeToReportCategory as STRC
from jeeves.util.date_util import datetime_to_str


class SpikeCategory(Enum):
    """
    Designator for different categories of spike analysis.
    """

    EXTERNAL_STR_SPIKES = auto()
    INTERNAL_STR_SPIKES = auto()
    ALL_STR_SPIKES = auto()
    EXTERNAL_NON_STR_SPIKES = auto()
    INTERNAL_NON_STR_SPIKES = auto()
    ALL_NON_STR_SPIKES = auto()
    EXTERNAL_V2_IOS_SPIKES = auto()
    INTERNAL_V2_IOS_SPIKES = auto()
    ALL_V2_IOS_SPIKES = auto()
    ALL_SPIKES = auto()
    COLD_START_SPIKES = auto()
    BASELINE_FREQ_COLD_START_SPIKES = auto()

    @classmethod
    def _get_shake_to_report_categories_for_spike_category(
        cls, spike_category: "SpikeCategory"
    ) -> Optional[List[STRC]]:
        # These spike categories only filter on Shake-To-Report categories.
        spike_category_to_str_categories = {
            cls.EXTERNAL_STR_SPIKES: [STRC.EXTERNAL],
            cls.INTERNAL_STR_SPIKES: [STRC.INTERNAL],
            cls.ALL_STR_SPIKES: [STRC.EXTERNAL, STRC.INTERNAL],
            cls.EXTERNAL_NON_STR_SPIKES: [STRC.NON_STR_EXTERNAL],
            cls.INTERNAL_NON_STR_SPIKES: [STRC.NON_STR_INTERNAL],
            cls.ALL_NON_STR_SPIKES: [STRC.NON_STR_EXTERNAL, STRC.NON_STR_INTERNAL],
        }
        return spike_category_to_str_categories.get(spike_category)

    @classmethod
    def get_predicate_for_category(
        cls, group_category: "SpikeCategory"
    ) -> Callable[[JeevesDocument], bool]:
        """
        Returns a predicate for testing whether a JeevesDocument should be included in spike
        analysis for the given spike category.

        Parameters:
            group_category: The SpikeCategory we want to check for.

        Returns:
            a lambda for testing a single JeevesDocument.
        """
        shake_to_report_categories = cls._get_shake_to_report_categories_for_spike_category(
            group_category
        )
        if shake_to_report_categories is not None:
            return lambda doc: doc.shake_to_report_category in shake_to_report_categories

        else:
            category_to_predicate: Dict[SpikeCategory, Callable[[JeevesDocument], bool]] = {
                cls.EXTERNAL_V2_IOS_SPIKES: lambda doc: bool(
                    doc.duolingo_metadata.get("user_information", {}).get("ios_v2_dev", False)
                )
                and doc.shake_to_report_category == STRC.EXTERNAL,
                cls.INTERNAL_V2_IOS_SPIKES: lambda doc: bool(
                    doc.duolingo_metadata.get("user_information", {}).get("ios_v2_dev", False)
                )
                and doc.shake_to_report_category == STRC.INTERNAL,
                cls.ALL_V2_IOS_SPIKES: lambda doc: bool(
                    doc.duolingo_metadata.get("user_information", {}).get("ios_v2_dev", False)
                ),
                cls.COLD_START_SPIKES: lambda doc: doc.date_time
                > datetime.strptime(COLD_START_DATE, "%Y-%m-%d-%z"),
                cls.BASELINE_FREQ_COLD_START_SPIKES: lambda doc: doc.date_time
                > datetime.strptime(COLD_START_DATE, "%Y-%m-%d-%z"),
                cls.ALL_SPIKES: lambda doc: True,
            }
            return category_to_predicate[group_category]

    @classmethod
    def get_elasticsearch_transformer_for_category(
        cls, group_category: "SpikeCategory"
    ) -> Callable[[Search], Search]:
        """
        Returns an Elasticsearch query dict that will filter JeevesDocuments that should be
        included in spike analysis for the given spike category.

        Parameters:
            group_category: The SpikeCategory we want to check for.

        Returns:
            a dict specifying an Elasticsearch query that filters JeevesDocuments.
        """

        shake_to_report_categories = cls._get_shake_to_report_categories_for_spike_category(
            group_category
        )
        if shake_to_report_categories is not None:
            return lambda s: s.filter(
                "terms",
                shake_to_report_category=[category.name for category in shake_to_report_categories],
            )

        else:
            category_to_query: Dict[SpikeCategory, Callable[[Search], Search]] = {
                cls.EXTERNAL_V2_IOS_SPIKES: lambda s: s.filter(
                    "term", duolingo_metadata__user_information__ios_v2_dev=True
                ).filter("term", shake_to_report_category=STRC.EXTERNAL.name),
                cls.INTERNAL_V2_IOS_SPIKES: lambda s: s.filter(
                    "term", duolingo_metadata__user_information__ios_v2_dev=True
                ).filter("term", shake_to_report_category=STRC.INTERNAL.name),
                cls.ALL_V2_IOS_SPIKES: lambda s: s.filter(
                    "term", duolingo_metadata__user_information__ios_v2_dev=True
                ),
                cls.COLD_START_SPIKES: lambda s: s.filter(
                    "range",
                    date_time={
                        "gte": datetime_to_str(datetime.strptime(COLD_START_DATE, "%Y-%m-%d-%z"))
                    },
                ),
                cls.BASELINE_FREQ_COLD_START_SPIKES: lambda s: s.filter(
                    "range",
                    date_time={
                        "gte": datetime_to_str(datetime.strptime(COLD_START_DATE, "%Y-%m-%d-%z"))
                    },
                ),
                cls.ALL_SPIKES: lambda s: s,
            }
            return category_to_query[group_category]

    @classmethod
    def get_jeeves_query_params_for_category(
        cls, group_category: "SpikeCategory"
    ) -> Dict[str, str]:
        """
        Returns query parameters for the /discovery and /analysis pages that will filter
        JeevesDocuments that should be included in spike analysis for the given spike category.

        Parameters:
            group_category: The SpikeCategory we want to check for.

        Returns:
            query parameters as a dictionary. For example:
            {
                "q": "duolingo app",
                "filter": "INTERNAL",
            }
            this means that https://jeeves.duolingo.com/en/discovery?q=duolingo%20app&filter=INTERNAL&id=JIRA_175258
            would display only tickets that fall under this spike category.

            Note that returned parameter values are NOT escaped.
        """

        shake_to_report_categories = cls._get_shake_to_report_categories_for_spike_category(
            group_category
        )
        if shake_to_report_categories is not None:
            if len(shake_to_report_categories) == 1:
                return {"filter": shake_to_report_categories[0].name}

            return {
                "q": f"shake_to_report_category:({'|'.join([category.name for category in shake_to_report_categories])})"
            }

        else:
            category_to_query: Dict[SpikeCategory, str] = {
                cls.EXTERNAL_V2_IOS_SPIKES: {
                    "q": "duolingo_metadata.user_information.ios_v2_dev:true",
                    "filter": "EXTERNAL",
                },
                cls.INTERNAL_V2_IOS_SPIKES: {
                    "q": "duolingo_metadata.user_information.ios_v2_dev:true",
                    "filter": "INTERNAL",
                },
                cls.ALL_V2_IOS_SPIKES: {
                    "q": "duolingo_metadata.user_information.ios_v2_dev:true",
                },
                cls.ALL_V2_IOS_SPIKES: {
                    "q": "duolingo_metadata.user_information.ios_v2_dev:true",
                },
                cls.COLD_START_SPIKES: {"from": f"{COLD_START_DATE}T04%3A00%3A00.000Z"},
                cls.BASELINE_FREQ_COLD_START_SPIKES: {
                    "from": f"{COLD_START_DATE}T04%3A00%3A00.000Z"
                },
                cls.ALL_SPIKES: {},
            }
            return category_to_query[group_category]
