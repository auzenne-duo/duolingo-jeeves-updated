from datetime import date
from enum import Enum, auto
from typing import Callable, Dict, List, Optional

from elasticsearch_dsl import Search

from jeeves.model.jeeves_document import JeevesDocument
from jeeves.model.shake_to_report_category import ShakeToReportCategory as STRC
from jeeves.util.date_util import str_to_date


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
    POSEIDON_IOS_ROW_BLASTER = auto()
    SFEAT_IOS_SIDE_QUESTS = auto()

    @classmethod
    def _get_deprecated_date_for_spike_category(
        cls, spike_category: "SpikeCategory"
    ) -> Optional[date]:
        spike_category_to_deprecated_date = {
            cls.EXTERNAL_V2_IOS_SPIKES: str_to_date("2022-09-23"),
            cls.INTERNAL_V2_IOS_SPIKES: str_to_date("2022-09-23"),
            cls.ALL_V2_IOS_SPIKES: str_to_date("2022-09-23"),
        }
        return spike_category_to_deprecated_date.get(spike_category)

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

        deprecated_date = cls._get_deprecated_date_for_spike_category(group_category)
        category_to_predicate: Dict[SpikeCategory, Callable[[JeevesDocument], bool]] = {
            cls.EXTERNAL_V2_IOS_SPIKES: lambda doc: bool(
                doc.duolingo_metadata.get("user_information", {}).get("ios_v2_dev", False)
            )
            and doc.shake_to_report_category == STRC.EXTERNAL
            and (deprecated_date is None or doc.date_time.date() <= deprecated_date),
            cls.INTERNAL_V2_IOS_SPIKES: lambda doc: bool(
                doc.duolingo_metadata.get("user_information", {}).get("ios_v2_dev", False)
            )
            and doc.shake_to_report_category == STRC.INTERNAL
            and (deprecated_date is None or doc.date_time.date() <= deprecated_date),
            cls.ALL_V2_IOS_SPIKES: lambda doc: bool(
                doc.duolingo_metadata.get("user_information", {}).get("ios_v2_dev", False)
            )
            and (deprecated_date is None or doc.date_time.date() <= deprecated_date),
            cls.ALL_SPIKES: lambda doc: True,
            cls.POSEIDON_IOS_ROW_BLASTER: lambda doc: doc.experiment_conditions.get(
                "poseidon_ios_mm_row_blaster", ""
            )
            in ["price_150", "price_250"],
            cls.SFEAT_IOS_SIDE_QUESTS: lambda doc: doc.experiment_conditions.get(
                "sfeat_ios_side_quests", ""
            )
            in ["free_for_premium_users", "paid_for_all_users"],
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

        deprecated_date = cls._get_deprecated_date_for_spike_category(group_category)
        timestamp_dict = {
            "time_zone": "America/New_York",
            "lte": deprecated_date,
        }
        category_to_query: Dict[SpikeCategory, Callable[[Search], Search]] = {
            cls.EXTERNAL_V2_IOS_SPIKES: lambda s: s.filter(
                "term", duolingo_metadata__user_information__ios_v2_dev=True
            )
            .filter("term", shake_to_report_category=STRC.EXTERNAL.name)
            .filter("range", date_time=timestamp_dict),
            cls.INTERNAL_V2_IOS_SPIKES: lambda s: s.filter(
                "term", duolingo_metadata__user_information__ios_v2_dev=True
            )
            .filter("term", shake_to_report_category=STRC.INTERNAL.name)
            .filter("range", date_time=timestamp_dict),
            cls.ALL_V2_IOS_SPIKES: lambda s: s.filter(
                "term", duolingo_metadata__user_information__ios_v2_dev=True
            ).filter("range", date_time=timestamp_dict),
            cls.ALL_SPIKES: lambda s: s,
            cls.POSEIDON_IOS_ROW_BLASTER: lambda s: s.filter(
                "terms",
                experiment_conditions__poseidon_ios_mm_row_blaster=["price_150", "price_250"],
            ),
            cls.SFEAT_IOS_SIDE_QUESTS: lambda s: s.filter(
                "terms",
                experiment_conditions__sfeat_ios_side_quests=[
                    "free_for_premium_users",
                    "paid_for_all_users",
                ],
            ),
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

        # TODO: I'm pretty sure this can mostly be removed because now the /tickets route uses the spike category to filter so this is unnecessary
        shake_to_report_categories = cls._get_shake_to_report_categories_for_spike_category(
            group_category
        )
        if shake_to_report_categories is not None:
            if len(shake_to_report_categories) == 1:
                return {"filter": shake_to_report_categories[0].name}

            return {
                "q": f"shake_to_report_category:({'|'.join([category.name for category in shake_to_report_categories])})"
            }

        deprecated_date = cls._get_deprecated_date_for_spike_category(group_category)
        if deprecated_date is not None:
            # This method is only used for formatting spike reporter messages to Slack.
            # The spike reporter should not be reporting spikes for deprecated.
            raise Exception("Attempted to form a Jeeves query for a deprecated spike category.")

        category_to_query: Dict[SpikeCategory, str] = {
            cls.ALL_SPIKES: {},
            cls.POSEIDON_IOS_ROW_BLASTER: {},
            cls.SFEAT_IOS_SIDE_QUESTS: {},
        }
        return category_to_query[group_category]
