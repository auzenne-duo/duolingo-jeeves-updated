"""
Our model for a ticket from the Zendesk API
"""
import base64
import json
import os
import re
import time
from hashlib import sha1
from typing import List

import attr
from requests import Response, Session

from jeeves import registry as app_registry
from jeeves.dal.monolith_dal import MonolithDAL
from jeeves.model.custom_types import JSON
from jeeves.model.jeeves_document import JeevesDocument
from jeeves.model.products import Products
from jeeves.model.shake_to_report_category import ShakeToReportCategory
from jeeves.model.supported_languages import SUPPORTED_LANGUAGES
from jeeves.util.classify import detect_language, detect_product
from jeeves.util.cleanup import (
    check_for_hyphen_line,
    clean_and_parse_description,
    extract_common_zendesk_headers,
    extract_duolingo_metadata,
)
from jeeves.util.date_util import parse_external_datetime
from jeeves.util.metadata_standardizer import MetaStdizer

_USER = os.environ.get("ZENDESK_REPORTS_USER")
_ZENDESK_API_TOKEN = os.environ.get("ZENDESK_API_TOKEN")
CONTRACTOR_EMAIL_DOMAIN = "@duolingocontractors.com"


@attr.s(kw_only=True)
class ZendeskDocument(JeevesDocument):
    email: str = attr.ib()
    product: str = attr.ib()
    priority: str = attr.ib()
    via: JSON = attr.ib()
    tags: List[str] = attr.ib()
    requester_id: str = attr.ib()
    # TODO: This metadata field is likely unused due to the introduction of the
    # duolingo_metadata field. Confirm its disuse and deprecate in future issue.
    metadata: JSON = attr.ib()

    @staticmethod
    def get_data_source_identifier() -> str:
        """
        Please see parent class for documentation
        """
        return "Zendesk"

    @classmethod
    def deserialize_from_external_json(cls, external_json: JSON) -> JeevesDocument:
        """
        Please see parent class for documentation
        """
        # If these seem like magic, they pretty much are. I talked to Ramya
        # and was told that these are the values we should filter on for
        # release candidate feedback.
        beta_indicators = ["bet40189", "betflight40190", "BETRC40190", "BET40189"]
        is_shake_to_report = False
        for beta_ind in beta_indicators:
            is_shake_to_report |= (
                beta_ind in external_json["tags"] or beta_ind in external_json["description"]
            )

        body_text = external_json["description"]
        duolingo_metadata = {}
        if is_shake_to_report or check_for_hyphen_line(body_text):
            body_text, duolingo_metadata = extract_duolingo_metadata(body_text)
        if not duolingo_metadata:
            body_text, duolingo_metadata = extract_common_zendesk_headers(body_text)

        _, metadata = clean_and_parse_description(body_text)
        header = external_json["subject"] if external_json["subject"] else ""

        link_url_base = "https://duolingotest.zendesk.com/agent"
        ticket_link = f"{link_url_base}/tickets/{external_json['id']}"
        user_link = f"{link_url_base}/users/{external_json['requester_id']}"

        aux_platform_information = ""
        android_platform_indicators = ["androidapp", "bug_report_android"]
        ios_platform_indicators = ["iphoneapp", "bug_report_ios"]
        web_platform_indicators = ["bug_report_web"]
        tags_set = set(external_json["tags"])
        if tags_set.intersection(android_platform_indicators):
            aux_platform_information = "Android"
        elif tags_set.intersection(ios_platform_indicators):
            aux_platform_information = "iOS"
        elif tags_set.intersection(web_platform_indicators):
            aux_platform_information = "Web"

        std_metadata = MetaStdizer.get_standardized_metadata(
            duolingo_metadata, aux_platform_information
        )

        channel = external_json["via"]["channel"]
        email = None
        if channel == "web" or channel == "api":
            with Session() as s:
                auth_str = f"{_USER}/token:{_ZENDESK_API_TOKEN}"
                b64_auth_str = base64.b64encode(auth_str.encode()).decode()
                s.headers.update({"Authorization": f"Basic {b64_auth_str}"})
                user_url = f"https://duolingotest.zendesk.com/api/v2/users/{external_json['requester_id']}.json"
                r = ZendeskDocument.rate_limited_get(s, user_url)
                j = json.loads(r.text)
                if "error" in j:
                    raise Exception("Error returned from Zendesk")
                email = j["user"]["email"]
        elif channel == "email":
            email = external_json["via"]["source"]["from"].get("address")
        user_id = None
        if email:
            user_id = app_registry(MonolithDAL).get_user_by_email_or_username(email)
            if CONTRACTOR_EMAIL_DOMAIN in email:
                is_shake_to_report = True
        elif std_metadata["username"]:
            user_id = app_registry(MonolithDAL).get_user_by_email_or_username(
                username=std_metadata["username"]
            )

        experiment_conditions_pattern = re.compile("^.*experiment_conditions\.txt$")
        experiment_conditions = {}
        for attachment_link in external_json["attachments"]:
            if experiment_conditions_pattern.match(attachment_link):
                with Session() as s:
                    auth_str = f"{_USER}/token:{_ZENDESK_API_TOKEN}"
                    b64_auth_str = base64.b64encode(auth_str.encode()).decode()
                    s.headers.update({"Authorization": f"Basic {b64_auth_str}"})
                    r = ZendeskDocument.rate_limited_get(s, attachment_link)
                    contents = r.text
                    for condition in re.findall("[a-zA-Z\d_]+: [a-zA-Z\d_]+", contents):
                        key, value = condition.split(": ")
                        experiment_conditions[key] = value

        return cls(
            data_source=cls.get_data_source_identifier(),
            document_id=str(external_json["id"]),
            jeeves_uid=f"{cls.get_data_source_identifier()}_{external_json['id']}",
            date_time=parse_external_datetime(external_json["created_at"]),
            header_text=header,
            body_text=body_text,
            language=SUPPORTED_LANGUAGES.filter_misc_languages(detect_language(body_text)),
            links=[ticket_link, user_link],
            shake_to_report_category=ShakeToReportCategory.EXTERNAL
            if is_shake_to_report
            else ShakeToReportCategory.NON_STR_EXTERNAL,
            attachments=external_json["attachments"],
            duolingo_metadata=duolingo_metadata,
            app_version=std_metadata["app_version"],
            challenge_id=std_metadata["challenge_id"],
            challenge_prompt_text=std_metadata["challenge_prompt_text"],
            challenge_type=std_metadata["challenge_type"],
            challenge_generator_specific_type=std_metadata["challenge_generator_specific_type"],
            course=std_metadata["course"],
            fullstory_url=std_metadata["fullstory_url"],
            lesson_number=std_metadata["lesson_number"],
            level_number=std_metadata["level_number"],
            os_version=std_metadata["os_version"],
            platform=std_metadata["platform"],
            screen_size=std_metadata["screen_size"],
            screen_content=std_metadata["screen_content"],
            session_bundle_id=std_metadata["session_bundle_id"],
            session_id=std_metadata["session_id"],
            session_type=std_metadata["session_type"],
            skill_id=std_metadata["skill_id"],
            skill_name=std_metadata["skill_name"],
            skill_tree_id=std_metadata["skill_tree_id"],
            ui_language=std_metadata["ui_language"],
            username=std_metadata["username"],
            email=email,
            product=detect_product(external_json["tags"], header).name,
            priority=external_json["priority"],
            via=external_json["via"],
            tags=external_json["tags"],
            requester_id=str(external_json["requester_id"]),
            metadata=metadata,
            embeddings={},
            experiment_conditions=experiment_conditions,
            user_id=user_id,
        )

    @classmethod
    def deserialize_from_internal_json(cls, internal_json: JSON) -> JeevesDocument:
        """
        Please see parent class for documentation
        """
        header = internal_json["header_text"] if internal_json["header_text"] else ""

        return cls(
            data_source=internal_json["data_source"],
            document_id=internal_json["document_id"],
            jeeves_uid=internal_json["jeeves_uid"],
            date_time=parse_external_datetime(internal_json["date_time"])
            if isinstance(internal_json["date_time"], str)
            else internal_json["date_time"],
            header_text=header,
            body_text=internal_json["body_text"],
            language=internal_json["language"],
            links=internal_json["links"],
            shake_to_report_category=ShakeToReportCategory[
                internal_json["shake_to_report_category"]
            ],
            attachments=internal_json["attachments"],
            duolingo_metadata=internal_json["duolingo_metadata"],
            app_version=internal_json["app_version"],
            challenge_id=internal_json.get("challenge_id", ""),
            challenge_prompt_text=internal_json.get("challenge_prompt_text", ""),
            challenge_type=internal_json.get("challenge_type", ""),
            challenge_generator_specific_type=internal_json.get(
                "challenge_generator_specific_type", ""
            ),
            course=internal_json["course"],
            fullstory_url=internal_json["fullstory_url"],
            lesson_number=internal_json.get("lesson_number", ""),
            level_number=internal_json.get("level_number", ""),
            os_version=internal_json["os_version"],
            platform=internal_json["platform"],
            screen_size=internal_json["screen_size"],
            screen_content=internal_json["screen_content"],
            session_bundle_id=internal_json.get("session_bundle_id", ""),
            session_id=internal_json.get("session_id", ""),
            session_type=internal_json.get("session_type", ""),
            skill_id=internal_json.get("skill_id", ""),
            skill_name=internal_json.get("skill_name", ""),
            skill_tree_id=internal_json.get("skill_tree_id", ""),
            ui_language=internal_json["ui_language"],
            username=internal_json["username"],
            product=internal_json["product"],
            email=internal_json.get("email", ""),
            priority=internal_json["priority"],
            via=internal_json["via"],
            tags=internal_json["tags"],
            requester_id=internal_json["requester_id"],
            metadata=internal_json["metadata"],
            embeddings=internal_json.get("embeddings", {}),
            experiment_conditions=internal_json.get("experiment_conditions", {}),
            user_id=internal_json.get("user_id", ""),
        )

    @classmethod
    def check_should_index_document(cls, document: JeevesDocument) -> bool:
        """
        Please see parent class for documentation
        """
        if not super().check_should_index_document(document):
            return False

        # Ignore tickets sent BY the following emails
        _SENDERS_TO_IGNORE = {
            "business@duolingo.com",
            "community@duolingo.com",
            "no-reply@duolingo.com",
        }
        # Also ignore tickets sent TO the following emails
        _RECEIVERS_TO_IGNORE = {
            "business@duolingo.com",
            "institution@testcenter.zendesk.com",
            "institutional@testcenter.zendesk.com",
            "luis@duolingo.com",
            "luis@duolingotest.zendesk.com",
            "privacy@duolingotest.zendesk.com",
            "support@duolingobusiness.zendesk.com",
            "testcenter-support@duolingo.com",
        }
        # Also also ignore tickets with one or more of the following tags
        _TAGS_TO_IGNORE = {
            "abuse",
            "accommodation",
            "accommodation_request",
            "appeal__r_flag_session",
            "appeal__m_flag_session",
            "appeal__s_flag_session",
            "blocked_account",
            "closed_by_merge",
            "duolingo_english_test___appeal_results",
            "duolingo_plus__account_access_issue",
            "host",
            "institutional",
            "outbound",
            "purchase_issue",
        }

        if document.via["channel"] == "chat":
            return False

        if document.via["source"]["rel"] == "follow_up":
            return False

        # Ignore a ticket if a sender email is on a blocklist
        from_data = document.via["source"]["from"]
        if from_data and "address" in from_data and from_data["address"] in _SENDERS_TO_IGNORE:
            return False

        # Ignore a ticket if receiving email is on a blocklist
        to_data = document.via["source"]["to"]
        if to_data and "address" in to_data and to_data["address"] in _RECEIVERS_TO_IGNORE:
            return False

        tag_data = document.tags
        if tag_data and set(tag_data) & _TAGS_TO_IGNORE:
            # TRI-4490: Only exclude by tag if it's NOT from a beta user (all beta user reports should be indexed)
            if document.shake_to_report_category not in [
                ShakeToReportCategory.EXTERNAL,
                ShakeToReportCategory.INTERNAL,
            ]:
                return False

        # Skip tickets that have an empty string ('') description
        # after cleanup, which are those that consist of just
        # punctuation/spacing after cleanup
        if not document.body_text:
            return False

        if document.product != Products.LA.name:
            return False

        return True

    @classmethod
    def generate_opensearch_internal_id(cls, document: JeevesDocument) -> str:
        """
        Please see parent class for documentation
        """
        # Using an insecure hash like SHA-1 is acceptable because this context
        # is not security critical
        hash_generator = sha1()

        hash_generator.update(document.get_data_source_identifier().encode())
        hash_generator.update(document.body_text.encode())
        hash_generator.update(document.requester_id.encode())

        return hash_generator.hexdigest()

    @staticmethod
    def rate_limited_get(s: Session, request_url: str) -> Response:
        """
        Zendesk has some rate limits in place that we need to respect. According to
        https://developer.zendesk.com/rest_api/docs/support/usage_limits, we can
        track the X-Rate-Limit-Remaining header and slow down our request frequency
        as we start to run out of requests. This function is a wrapper around
        Session.get() with such a modification.

        Parameters:
            s: The Session object that will be making our request.
            request_url: The URL we want to make a GET request to.

        Returns:
            The Response object returned by Session.get().
        """
        r = s.get(request_url)

        if r.status_code == 429:
            print("429 response due to rate-limiting. Sleeping.")
            if "Retry-After" in r.headers:
                time.sleep(int(r.headers["Retry-After"]))
            else:
                time.sleep(60)
            r = s.get(request_url)

        if "X-Rate-Limit-Remaining" in r.headers:
            remaining_limit = int(r.headers["X-Rate-Limit-Remaining"])
            # These values are pretty arbitrary
            # We need a gradual throttling like this because multiple instances
            # of this code can be running at once, all tied to the same Zendesk
            # account (i.e. prod, dev, and local dev all eat into the rate limit)
            if remaining_limit < 5:
                time.sleep(60)
            elif remaining_limit < 10:
                time.sleep(30)
            elif remaining_limit < 50:
                time.sleep(10)
            elif remaining_limit < 100:
                time.sleep(5)
            elif remaining_limit < 150:
                time.sleep(1)

        return r
