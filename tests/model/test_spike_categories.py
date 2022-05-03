from datetime import datetime
from typing import Optional

import pytest

from jeeves.model.jeeves_document import JeevesDocument
from jeeves.model.shake_to_report_category import ShakeToReportCategory
from jeeves.model.spike_categories import SpikeCategory
from jeeves.model.zendesk_document import ZendeskDocument


def _get_document(category: ShakeToReportCategory, ios_v2_dev: Optional[bool] = None):
    return ZendeskDocument(
        data_source="",
        document_id="",
        jeeves_uid="",
        date_time=datetime.now(),
        header_text="",
        body_text="",
        language="",
        links=[],
        shake_to_report_category=category,
        attachments=[],
        duolingo_metadata={"user_information": {"ios_v2_dev": ios_v2_dev}}
        if ios_v2_dev is not None
        else {},
        app_version="",
        course="",
        fullstory_url="",
        os_version="",
        platform="",
        screen_size="",
        screen_content="",
        ui_language="",
        username="",
        product="",
        priority="",
        via={},
        tags=[],
        requester_id="",
        metadata={},
    )


external_doc = _get_document(ShakeToReportCategory.EXTERNAL)
internal_doc = _get_document(ShakeToReportCategory.INTERNAL)
non_str_external_doc = _get_document(ShakeToReportCategory.NON_STR_EXTERNAL)
non_str_internal_doc = _get_document(ShakeToReportCategory.NON_STR_INTERNAL)

external_v2_doc = _get_document(ShakeToReportCategory.EXTERNAL, ios_v2_dev=True)
internal_v2_doc = _get_document(ShakeToReportCategory.INTERNAL, ios_v2_dev=True)
external_not_v2_doc = _get_document(ShakeToReportCategory.EXTERNAL, ios_v2_dev=False)
internal_not_v2_doc = _get_document(ShakeToReportCategory.INTERNAL, ios_v2_dev=False)

get_predicate_for_category_test_cases = [
    (SpikeCategory.EXTERNAL_STR_SPIKES, external_doc, True),
    (SpikeCategory.EXTERNAL_STR_SPIKES, non_str_external_doc, False),
    (SpikeCategory.ALL_NON_STR_SPIKES, internal_doc, False),
    (SpikeCategory.ALL_NON_STR_SPIKES, non_str_internal_doc, True),
    (SpikeCategory.EXTERNAL_V2_IOS_SPIKES, external_doc, False),
    (SpikeCategory.INTERNAL_V2_IOS_SPIKES, internal_v2_doc, True),
    (SpikeCategory.ALL_V2_IOS_SPIKES, external_v2_doc, True),
    (SpikeCategory.ALL_V2_IOS_SPIKES, internal_not_v2_doc, False),
    (SpikeCategory.ALL_SPIKES, external_doc, True),
]


@pytest.mark.parametrize("spike_category,doc,expected", get_predicate_for_category_test_cases)
def test_get_predicate_for_category(
    spike_category: SpikeCategory, doc: JeevesDocument, expected: bool
):
    assert SpikeCategory.get_predicate_for_category(spike_category)(doc) == expected


def test_get_predicate_for_every_category():
    for spike_category in SpikeCategory:
        SpikeCategory.get_predicate_for_category(spike_category)


def test_get_elasticsearch_transformer_for_category():
    for spike_category in SpikeCategory:
        SpikeCategory.get_elasticsearch_transformer_for_category(spike_category)
