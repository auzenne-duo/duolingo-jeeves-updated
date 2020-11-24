from enum import Enum, auto
from typing import List

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
