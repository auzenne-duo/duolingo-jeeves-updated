import unittest
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from jeeves.dal.elasticsearch_interface import ElasticsearchDAL
from jeeves.manager.jeeves_duplicate_manager import JeevesDuplicateManager
from jeeves.model.appfigures_document import AppfiguresDocument
from jeeves.model.jira_document import JiraDocument
from jeeves.model.shake_to_report_category import ShakeToReportCategory
from jeeves.model.zendesk_document import ZendeskDocument

now = datetime.now()


def _appfigures_document(header="I am a header", body="I am body text"):
    doc = AppfiguresDocument(
        data_source="AppFigures",
        document_id="doc1",
        jeeves_uid="uid1",
        date_time=now,
        header_text=header,
        body_text=body,
        language="en",
        links=[],
        shake_to_report_category=ShakeToReportCategory.EXTERNAL,
        attachments=[],
        duolingo_metadata={},
        app_version="",
        course="",
        fullstory_url="",
        os_version="",
        platform="",
        screen_size="",
        screen_content="",
        ui_language="",
        username="",
        author="",
        stars=5.0,
        iso="",
        version="",
        deleted=False,
        product_id="prod1",
        store="",
    )
    return doc


def _jira_document(header="I am a header", body="I am body text"):
    doc = JiraDocument(
        data_source="AppFigures",
        document_id="doc1",
        jeeves_uid="uid1",
        date_time=now,
        header_text=header,
        body_text=body,
        language="en",
        links=[],
        shake_to_report_category=ShakeToReportCategory.EXTERNAL,
        attachments=[],
        duolingo_metadata={},
        app_version="",
        course="",
        fullstory_url="",
        os_version="",
        platform="",
        screen_size="",
        screen_content="",
        ui_language="",
        username="",
        issue_key="DLAA-1111",
        issue_links=[],
        issue_type="Bug",
        project="DLAA",
        linked_duplicate_keys=[],
        creation_date=datetime.now,
        updated_date=datetime.now,
        resolution_date=datetime.now,
        status="Closed",
        resolution="Done",
        components=[],
        feature_url="",
        feature="",
        priority="High",
        reporter="",
        assignee="",
        comments=[],
        labels=[],
        embedding_vector=[],
    )
    return doc


def _zendesk_document(header="I am a header", body="I am body text"):
    doc = ZendeskDocument(
        data_source="Zendesk",
        document_id="doc1",
        jeeves_uid="uid1",
        date_time=now,
        header_text=header,
        body_text=body,
        language="en",
        links=[],
        shake_to_report_category=ShakeToReportCategory.EXTERNAL,
        attachments=[],
        duolingo_metadata={},
        app_version="",
        course="",
        fullstory_url="",
        os_version="",
        platform="",
        screen_size="",
        screen_content="",
        ui_language="",
        username="",
        product="LA",
        priority="urgent",
        via={
            "channel": "api",
            "source": {
                "from": {},
                "rel": None,
                "to": {},
            },
        },
        tags=[],
        requester_id="requester1",
        metadata="",
    )
    return doc


def _zendesk_email_document(
    sender="sender@email.com",
    recipient="recipient@email.com",
    header="I am a header",
    body="I am body text",
):
    doc = _zendesk_document(header=header, body=body)
    doc.via["channel"] = "email"
    doc.via["source"]["from"] = {"address": sender}
    doc.via["source"]["to"] = {"address": recipient}
    return doc


dedup_document_batch_test_cases = [
    ([], []),
    (
        [_appfigures_document(), _appfigures_document()],
        [_appfigures_document(), _appfigures_document()],
    ),
    ([_jira_document(), _jira_document()], [_jira_document(), _jira_document()]),
    ([_zendesk_document(), _zendesk_document()], [_zendesk_document(), _zendesk_document()]),
    ([_zendesk_email_document(), _zendesk_email_document()], [_zendesk_email_document()]),
    (
        [
            _zendesk_email_document(sender="", header="", body=""),
            _zendesk_email_document(sender="", header="", body=""),
        ],
        [_zendesk_email_document(sender="", header="", body="")],
    ),
    (
        [
            _zendesk_email_document(sender="user1@duolingo.com"),
            _zendesk_email_document(sender="user2@duolingo.com"),
        ],
        [
            _zendesk_email_document(sender="user1@duolingo.com"),
            _zendesk_email_document(sender="user2@duolingo.com"),
        ],
    ),
    (
        [_zendesk_email_document(header="Header 1"), _zendesk_email_document(header="Header 2")],
        [_zendesk_email_document(header="Header 1"), _zendesk_email_document(header="Header 2")],
    ),
    (
        [
            _zendesk_email_document(header="Body Text 1"),
            _zendesk_email_document(header="Body Text 2"),
        ],
        [
            _zendesk_email_document(header="Body Text 1"),
            _zendesk_email_document(header="Body Text 2"),
        ],
    ),
    (
        [
            _zendesk_email_document(recipient="recipient1@email.com"),
            _zendesk_email_document(recipient="recipient2@email.com"),
        ],
        [_zendesk_email_document(recipient="recipient1@email.com")],
    ),
]

recent_duplicate_exists_test_cases = [
    (_appfigures_document(), False),
    (_jira_document(), False),
    (_zendesk_document(), False),
    (_zendesk_email_document(), True),
]


elasticsearch_mock = ElasticsearchDAL()
elasticsearch_mock.get_recent_paginated_tickets = MagicMock(
    return_value=[_zendesk_email_document()]
)
duplicate_manager = JeevesDuplicateManager(elasticsearch_mock)


@pytest.mark.parametrize("input_documents,expected", dedup_document_batch_test_cases)
def test_dedup_document_batch(input_documents, expected):
    actual_documents = duplicate_manager.dedup_document_batch(input_documents)

    case = unittest.TestCase()
    case.assertCountEqual(expected, actual_documents)


@pytest.mark.parametrize("input_document,expected", recent_duplicate_exists_test_cases)
def test_recent_duplicate_exists(input_document, expected):
    assert expected == duplicate_manager.recent_duplicate_exists(input_document)
