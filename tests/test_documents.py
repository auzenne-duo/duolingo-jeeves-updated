from datetime import datetime
from typing import List

import numpy as np

from jeeves.config.config import GPT_EMBEDDING_MODEL
from jeeves.model.jeeves_document import JeevesDocument
from jeeves.model.shake_to_report_category import ShakeToReportCategory
from jeeves.model.zendesk_document import ZendeskDocument

now = datetime.now()


def _zendesk_document(
    document_id="default_doc",
    jeeves_uid="default_uid",
    date_time=now,
    header="I am a header",
    body="I am body text",
    embeddings=np.array([0, 0, 0]),
):
    doc = ZendeskDocument(
        data_source="Zendesk",
        document_id=document_id,
        jeeves_uid=jeeves_uid,
        date_time=date_time,
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
        embeddings=embeddings,
        email="",
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
        experiment_conditions={},
    )
    return doc


mock_jeeves_document_0 = _zendesk_document(
    document_id="0",
    jeeves_uid="uid0",
    header="Leaderboards are broken",
    date_time=datetime(2023, 5, 1, 23, 55, 59, 342380),
    body="@Duolingo when I click on the leaderboard tab the app crashes!",
    embeddings={GPT_EMBEDDING_MODEL: np.array([0.5, 0.5, 0.6])},
)
mock_jeeves_document_1 = _zendesk_document(
    document_id="1",
    jeeves_uid="uid1",
    header="Please add swahili",
    body="I really want to use Duolingo to learn swahili",
    embeddings={GPT_EMBEDDING_MODEL: np.array([10000, 200, 0.00002])},
)
mock_jeeves_document_2 = _zendesk_document(
    document_id="2",
    jeeves_uid="uid2",
    date_time=datetime(2022, 1, 18),
    header="Leagues are so much fun",
    body="I finally got first in the diamond league!",
    embeddings={GPT_EMBEDDING_MODEL: np.array([0.5, 0.5, 0.7])},
)
mock_jeeves_document_3 = _zendesk_document(
    document_id="3",
    jeeves_uid="uid3",
    date_time=datetime(2023, 5, 1, 2, 5, 59),
    header="How do I see my friends on the leaderboard?",
    body="I want to be in a league with my friends!",
    embeddings={GPT_EMBEDDING_MODEL: np.array([0.5, 0.5, 0.55])},
)
mock_jeeves_document_4 = _zendesk_document(
    document_id="4",
    jeeves_uid="uid4",
    header="Duolingo is so competitive",
    body="Duolingo makes me feel like I'm competing with my swahili friends",
    embeddings={GPT_EMBEDDING_MODEL: np.array([0.5, 0.51, 0.55])},
)
mock_jeeves_document_5 = _zendesk_document(
    document_id="5",
    jeeves_uid="uid5",
    date_time=datetime(2022, 1, 18, 8, 15, 16, 23),
    header="Please add more leagues",
    body="The diamond league is way too easy for me! I want a real challenge!",
)
mock_jeeves_document_6 = _zendesk_document(
    document_id="6",
    jeeves_uid="uid6",
    date_time=datetime(2022, 1, 18, 23),
    header="I made it to the pearl league!",
    body="I'm so excited!",
)
mock_jeeves_document_7 = _zendesk_document(
    document_id="7",
    jeeves_uid="uid7",
    date_time=datetime(2023, 5, 1, 2, 3, 4, 5),
    header="Leaderboards are making me sad",
    body="I don't have time to get 10,000 xp a week!",
)
mock_jeeves_document_8 = _zendesk_document(
    document_id="8",
    jeeves_uid="uid8",
    date_time=datetime(2022, 1, 18, 23, 8, 9, 34),
    header="I've been in the diamond league for 10 weeks straight!",
    body="I'm learning so much while trying to stay in the diamond league!",
)


def get_mock_jeeves_documents() -> List[JeevesDocument]:
    return [
        mock_jeeves_document_0,
        mock_jeeves_document_1,
        mock_jeeves_document_2,
        mock_jeeves_document_3,
        mock_jeeves_document_4,
        mock_jeeves_document_5,
        mock_jeeves_document_6,
        mock_jeeves_document_7,
        mock_jeeves_document_8,
    ]
