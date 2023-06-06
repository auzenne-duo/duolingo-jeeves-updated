from datetime import datetime
from typing import Dict, Optional

import pytest

from jeeves.model.jeeves_document import JeevesDocument
from jeeves.model.shake_to_report_category import ShakeToReportCategory
from jeeves.model.spike_categories import SpikeCategory
from jeeves.model.zendesk_document import ZendeskDocument


def _get_document(category: ShakeToReportCategory, is_new: bool, ios_v2_dev: Optional[bool] = None):
    return ZendeskDocument(
        data_source="",
        document_id="",
        jeeves_uid="",
        date_time=datetime(year=2022, month=10, day=1)
        if is_new
        else datetime(year=2022, month=9, day=1),
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
        email="",
        product="",
        priority="",
        via={},
        tags=[],
        requester_id="",
        metadata={},
        experiment_conditions={},
    )


external_doc = _get_document(ShakeToReportCategory.EXTERNAL, False)
internal_doc = _get_document(ShakeToReportCategory.INTERNAL, False)
non_str_external_doc = _get_document(ShakeToReportCategory.NON_STR_EXTERNAL, False)
non_str_internal_doc = _get_document(ShakeToReportCategory.NON_STR_INTERNAL, False)

external_v2_doc = _get_document(ShakeToReportCategory.EXTERNAL, False, ios_v2_dev=True)
internal_v2_doc = _get_document(ShakeToReportCategory.INTERNAL, False, ios_v2_dev=True)
new_external_v2_doc = _get_document(ShakeToReportCategory.EXTERNAL, True, ios_v2_dev=True)
new_internal_v2_doc = _get_document(ShakeToReportCategory.INTERNAL, True, ios_v2_dev=True)
external_not_v2_doc = _get_document(ShakeToReportCategory.EXTERNAL, False, ios_v2_dev=False)
internal_not_v2_doc = _get_document(ShakeToReportCategory.INTERNAL, False, ios_v2_dev=False)

get_predicate_for_category_test_cases = [
    (SpikeCategory.EXTERNAL_STR_SPIKES, external_doc, True),
    (SpikeCategory.EXTERNAL_STR_SPIKES, non_str_external_doc, False),
    (SpikeCategory.ALL_NON_STR_SPIKES, internal_doc, False),
    (SpikeCategory.ALL_NON_STR_SPIKES, non_str_internal_doc, True),
    (SpikeCategory.ALL_SPIKES, external_doc, True),
]


@pytest.mark.parametrize("spike_category,doc,expected", get_predicate_for_category_test_cases)
def test_get_predicate_for_category(
    spike_category: SpikeCategory, doc: JeevesDocument, expected: bool
):
    assert SpikeCategory.get_predicate_for_category(spike_category)(doc) == expected


get_jeeves_query_params_for_category_test_cases = [
    (SpikeCategory.EXTERNAL_STR_SPIKES, {"filter": "EXTERNAL"}),
    (
        SpikeCategory.ALL_NON_STR_SPIKES,
        {"q": "shake_to_report_category:(NON_STR_EXTERNAL|NON_STR_INTERNAL)"},
    ),
]


@pytest.mark.parametrize("spike_category,expected", get_jeeves_query_params_for_category_test_cases)
def test_get_jeeves_query_params_for_category(
    spike_category: SpikeCategory, expected: Dict[str, str]
):
    assert SpikeCategory.get_jeeves_query_params_for_category(spike_category) == expected


def test_get_predicate_for_every_category():
    for spike_category in SpikeCategory:
        SpikeCategory.get_predicate_for_category(spike_category)


def test_get_opensearch_transformer_for_every_category():
    for spike_category in SpikeCategory:
        SpikeCategory.get_opensearch_transformer_for_category(spike_category)


def test_get_jeeves_query_params_for_every_active_category():
    for spike_category in [
        SpikeCategory.EXTERNAL_STR_SPIKES,
        SpikeCategory.INTERNAL_STR_SPIKES,
        SpikeCategory.ALL_STR_SPIKES,
        SpikeCategory.EXTERNAL_NON_STR_SPIKES,
        SpikeCategory.INTERNAL_NON_STR_SPIKES,
        SpikeCategory.ALL_NON_STR_SPIKES,
        SpikeCategory.ALL_SPIKES,
    ]:
        SpikeCategory.get_jeeves_query_params_for_category(spike_category)
