from enum import Enum, auto
from typing import Callable, List

from elasticsearch_dsl import Search

from jeeves.model.shake_to_report_category import ShakeToReportCategory as STRC


class SpikeCategory(Enum):
    """
    Designator for different categories of spike analysis.
    Right now just contains different combinations of shake-to-report categories.
    """

    EXTERNAL_STR_SPIKES = auto()
    INTERNAL_STR_SPIKES = auto()
    ALL_STR_SPIKES = auto()
    EXTERNAL_NON_STR_SPIKES = auto()
    INTERNAL_NON_STR_SPIKES = auto()
    ALL_NON_STR_SPIKES = auto()
    ALL_SPIKES = auto()

    @classmethod
    def inter_category_mapping(cls, group_category: "SpikeCategory") -> List[STRC]:
        """
        Maps a SpikeCategory to one or more ShakeToReportCategories.
        Used for determining which groups of documents should be combined
        during spike analysis.

        Parameters:
            group_category: Input to the mapping

        Returns:
            One or more ShakeToReportCategories that represent the output of the mapping.
        """

        # It irks me that this is still the best way to do a switch statement
        case_logic = {
            cls.EXTERNAL_STR_SPIKES: [STRC.EXTERNAL],
            cls.INTERNAL_STR_SPIKES: [STRC.INTERNAL],
            cls.ALL_STR_SPIKES: [STRC.EXTERNAL, STRC.INTERNAL],
            cls.EXTERNAL_NON_STR_SPIKES: [STRC.NON_STR_EXTERNAL],
            cls.INTERNAL_NON_STR_SPIKES: [STRC.NON_STR_INTERNAL],
            cls.ALL_NON_STR_SPIKES: [STRC.NON_STR_EXTERNAL, STRC.NON_STR_INTERNAL],
            cls.ALL_SPIKES: [
                STRC.EXTERNAL,
                STRC.INTERNAL,
                STRC.NON_STR_EXTERNAL,
                STRC.NON_STR_INTERNAL,
            ],
        }
        return case_logic[group_category]

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

        shake_to_report_categories = cls.inter_category_mapping(group_category)
        if shake_to_report_categories is not None:
            return lambda s: s.filter(
                "terms",
                shake_to_report_category=[category.name for category in shake_to_report_categories],
            )
        else:
            return lambda s: s
