import json
import logging
import os
from datetime import datetime
from typing import Dict, List

from duolingo_base.util import registry

from jeeves.config.config import JIRA_ISSUE_TYPE_BUG, QUALITY_REPORT_S3_PATH
from jeeves.dal.opensearch_interface import OpenSearchDAL
from jeeves.manager.duplicate_graph_resolver import DuplicateGraphResolver
from jeeves.manager.jira_manager import JiraManager
from jeeves.model.custom_types import JSON
from jeeves.model.jira_document import JiraDocument
from jeeves.model.quality_report import (
    QualityReport,
    QualityReportIssueDataset,
    QualityScoreHistory,
)
from jeeves.model.quality_score_params import QualityScoreParams
from jeeves.util.date_util import date_to_str
from jeeves.util.json_encoder import JeevesJSONEncoder
from jeeves.util.quality_report_util import PROJECT_TO_CLIENT, QUALITY_REPORT_OVERALL_KEY
from jeeves.util.s3_client_and_bucket import download_from_jeeves_s3, upload_to_jeeves_s3

LOG = logging.getLogger(__name__)
_CHECKPOINT_FILENAME = "checkpoint"
_QUALITY_ISSUE_DATSETS_FILENAME = "quality_issue_datasets"
_QUALITY_REPORT_DATA_FOLDER = "quality_report_data"
_INWARD_ISSUE_LINK_KEY = "inwardIssue"
_OUTWARD_ISSUE_LINK_KEY = "outwardIssue"
_POSSIBLE_DEV_ISSUE_LINKS = {"Relates", "Is caused by", "Is blocked by"}
_PROJECT_TO_SCORES_FILENAME = "project_to_scores"
_NUM_PAST_DATASETS_TO_STORE = 4


@registry.bind(
    duplicate_graph_resolver=registry.reference(DuplicateGraphResolver),
    jira_manager=registry.reference(JiraManager),
    opensearch_dal=registry.reference(OpenSearchDAL),
)
class QualityReportDAL:
    def __init__(
        self,
        duplicate_graph_resolver: DuplicateGraphResolver,
        jira_manager: JiraManager,
        opensearch_dal: OpenSearchDAL,
    ) -> None:
        self.duplicate_graph_resolver = duplicate_graph_resolver
        self.jira_manager = jira_manager
        self.opensearch_dal = opensearch_dal

    def _get_quality_scores_filepath(self, title: str) -> str:
        """
        Returns a filepath as a string for the quality issue scores in s3

        Params:
            title: string title of the area or team
        """
        return os.path.join(QUALITY_REPORT_S3_PATH, title, _PROJECT_TO_SCORES_FILENAME)

    def get_past_quality_scores(self, title: str) -> Dict[str, QualityScoreHistory]:
        """
        gets the past quality scores for each project and Overall

        returns:
            dictionary of the following structure :
                "Overall": QualityScoreHistory
                "DLAA": ...
                "DLAI": ...
                "DLAA": ...
        """
        try:
            return json.loads(download_from_jeeves_s3(self._get_quality_scores_filepath(title)))
        except:
            LOG.warning(f"Could not find quality report scores for {title}")
            return {QUALITY_REPORT_OVERALL_KEY: [], "DLAA": [], "DLAI": [], "DLAW": []}

    def upload_quality_scores_to_s3(self, quality_report: QualityReport):
        """
        Uploads quality report scores to s3

        Params:
            project_to_scores: dictionary of the format {"DLAA": QualityScoreHistory ...},  includes Overall, DLAA, DLAI, DLAW
        """
        upload_to_jeeves_s3(
            self._get_quality_scores_filepath(quality_report.title),
            json.dumps(quality_report.project_to_scores),
        )

    def _get_quality_issue_datasets_filepath(self, title: str) -> str:
        """
        Returns a filepath as a string for the quality issue datasets in s3

        Params:
            title: string title of the area or team
        """
        return os.path.join(QUALITY_REPORT_S3_PATH, title, _QUALITY_ISSUE_DATSETS_FILENAME)

    def get_past_quality_issue_datasets(self, title: str) -> List[QualityReportIssueDataset]:
        """
        gets the issues used in past quality reports

        Params
            title: string name for an area or team, such as "Growth"

        returns:
            list of QualityReportIssueDatasets
        """
        try:
            serialized_datasets = json.loads(
                download_from_jeeves_s3(
                    self._get_quality_issue_datasets_filepath(title) + f"_{title}"
                )
            )
            quality_report_datasets = []
            for dataset in serialized_datasets:
                quality_report_dataset = QualityReportIssueDataset.from_dict(dataset)
                self.update_jira_issues_with_score_params(quality_report_dataset.issues)
                quality_report_datasets.append(quality_report_dataset)
            return quality_report_datasets
        except:
            LOG.warning(f"Could not find quality report issue datasets for {title}")
            return []

    def upload_quality_issue_datasets(self, quality_report: QualityReport) -> None:
        """
        Uploads the jira documents used in the latests quality report

        Params
            quality_report: quality report object for which the issues should be stored
        """
        title = quality_report.title
        upload_to_jeeves_s3(
            self._get_quality_issue_datasets_filepath(title),
            json.dumps(
                [
                    dataset.serialize()
                    for dataset in quality_report.issue_datasets[:_NUM_PAST_DATASETS_TO_STORE]
                ],
                cls=JeevesJSONEncoder,
            ),
        )

    def _get_quality_report_checkpoint_filepath(self, title: str) -> str:
        """
        Returns the filepath for the checkpoint file in s3 for a given area or team
        """
        return os.path.join(
            QUALITY_REPORT_S3_PATH, title, _QUALITY_REPORT_DATA_FOLDER, _CHECKPOINT_FILENAME
        )

    def _get_serialized_quality_report_filepath(self, title: str, checkpoint_date: str) -> str:
        """
        Returns the filepath for the serialized quality report in s3 for a given area or team
        """
        return os.path.join(
            QUALITY_REPORT_S3_PATH, title, _QUALITY_REPORT_DATA_FOLDER, checkpoint_date
        )

    def get_latest_serialized_quality_report(self, title: str) -> JSON:
        """
        Downloads the latest quality report

        Params
            title: string name for an area or team, such as "Growth"

        Returns: JSON object of SerializedQualityReportData structure
        """
        # get the checkpoint date for the latest quality report
        checkpoint_date = json.loads(
            download_from_jeeves_s3(self._get_quality_report_checkpoint_filepath(title))
        )
        return download_from_jeeves_s3(
            self._get_serialized_quality_report_filepath(title, checkpoint_date)
        )

    def upload_serialized_quality_report(self, quality_report: QualityReport) -> None:
        """
        Uploads the serialized version of the latest quality report

        Params
            quality_report: quality report object for which the issues should be stored
        """
        end_date_str = date_to_str(quality_report.end_date)
        serialized_quality_report = quality_report.serialize()
        upload_to_jeeves_s3(
            self._get_serialized_quality_report_filepath(quality_report.title, end_date_str),
            json.dumps(serialized_quality_report, cls=JeevesJSONEncoder),
        )
        # update the checkpoint file
        upload_to_jeeves_s3(
            self._get_quality_report_checkpoint_filepath(quality_report.title),
            json.dumps(end_date_str),
        )

    def filter_dev_related_issues(
        self, jira_docs: List[JiraDocument], key_to_issue_map: Dict[str, JiraDocument]
    ) -> List[JiraDocument]:
        """
        Filters out issues that are related to a development ticket,
        where a dev ticket is a non-bug ticket.

        Params:
            issue_keys: list of issue keys
            key_to_issue_map: mapping from issue key to JiraDocument

        Returns:
            list of jira documents that are not related to a dev issue
        """
        issues_to_fetch = set()
        for jira_doc in jira_docs:
            for link in jira_doc.issue_links:
                if any(
                    [link_type in link["type"]["name"] for link_type in _POSSIBLE_DEV_ISSUE_LINKS]
                ):
                    if _INWARD_ISSUE_LINK_KEY in link:
                        issues_to_fetch.add(link[_INWARD_ISSUE_LINK_KEY]["key"])
                    if _OUTWARD_ISSUE_LINK_KEY in link:
                        issues_to_fetch.add(link[_OUTWARD_ISSUE_LINK_KEY]["key"])

        downloaded_issues = self.jira_manager.download_bulk_issues_with_features(
            list(issues_to_fetch)
        )
        key_to_issue_map.update({issue.issue_key: issue for issue in downloaded_issues})
        filtered_jira_docs = []
        for jira_doc in jira_docs:
            is_dev_related = False
            for link in jira_doc.issue_links:
                if any(
                    [link_type in link["type"]["name"] for link_type in _POSSIBLE_DEV_ISSUE_LINKS]
                ):
                    issue = None
                    if _INWARD_ISSUE_LINK_KEY in link:
                        issue = key_to_issue_map.get(link[_INWARD_ISSUE_LINK_KEY]["key"])
                    if _OUTWARD_ISSUE_LINK_KEY in link:
                        issue = key_to_issue_map.get(link[_OUTWARD_ISSUE_LINK_KEY]["key"])
                    if issue is None:
                        LOG.debug(f"Missing linked issue {link}")
                        continue
                    if issue.issue_type != JIRA_ISSUE_TYPE_BUG:
                        is_dev_related = True
                        break
            if not is_dev_related:
                filtered_jira_docs.append(jira_doc)
        return filtered_jira_docs

    def get_quality_report_issues(self, start_date: datetime) -> List[JiraDocument]:
        """
        Returns a list of jira issues that have been updated since the start_date. Duplicate issues
        are filtered out, as well as any issue related to a dev issue (a non-bug jira issue)
        Jira documents are updated to have the quality_score_params field set
        """
        jira_docs = JiraManager.get_jira_issues_since(date_to_str(start_date))
        LOG.debug(f"resolving duplicate graphs")
        jira_docs, key_to_issue_map = self.duplicate_graph_resolver.resolve_duplicate_graphs(
            jira_docs
        )
        jira_docs = self.filter_dev_related_issues(jira_docs, key_to_issue_map)

        self.update_jira_issues_with_score_params(jira_docs)
        return jira_docs

    def update_jira_issues_with_score_params(self, jira_docs: List[JiraDocument]) -> None:
        """
        Given a list of JiraDocuments, updates the JiraDocument's score field
        with the score from the quality report.
        """
        for doc in jira_docs:
            doc.quality_score_params = QualityScoreParams.init_from_jira_data(
                doc.creation_date, doc.priority, doc.resolution_date, doc.labels, doc.resolution
            )
            doc.client = PROJECT_TO_CLIENT.get(doc.project)
