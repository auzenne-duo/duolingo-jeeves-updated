"""
A manager for all tasks related to sentiment analysis
"""
from typing import Dict, List, Union

from duolingo_base.util import registry

from jeeves.config.config import GPT_EMBEDDING_MODEL
from jeeves.dal.ai_completions_dal import AICompletionsDAL
from jeeves.model.jeeves_document import JeevesDocument
from jeeves.util.polarity_calculator import calc_cosine_similarity

SYSTEM_PROMPT = """
This is a list of fields for a python object called a JeevesDocument

    data_source: str = attr.ib()
    document_id: str = attr.ib()
    jeeves_uid: str = attr.ib()
    date_time: datetime.datetime = attr.ib()
    header_text: str = attr.ib(default="")
    body_text: str = attr.ib()
    is_bug: bool = attr.ib(default=True)
    language: str = attr.ib()
    lemmatized_terms: List[str] = attr.ib(default=[])
    links: List[str] = attr.ib(default=[])
    shake_to_report_category: ShakeToReportCategory = attr.ib()
    attachments: List[str] = attr.ib()
    duolingo_metadata: Dict[str, JSON] = attr.ib()
    app_version: str = attr.ib()
    challenge_id: str = attr.ib(default="")
    challenge_prompt_text: str = attr.ib(default="")
    challenge_type: str = attr.ib(default="")
    challenge_generator_specific_type: str = attr.ib(default="")
    course: str = attr.ib()
    fullstory_url: str = attr.ib()
    lesson_number: str = attr.ib(default="")
    level_number: str = attr.ib(default="")
    os_version: str = attr.ib()
    platform: str = attr.ib()
    screen_size: str = attr.ib()
    screen_content: str = attr.ib()
    session_bundle_id: str = attr.ib(default="")
    session_id: str = attr.ib(default="")
    session_type: str = attr.ib(default="")
    skill_id: str = attr.ib(default="")
    skill_name: str = attr.ib(default="")
    skill_tree_id: str = attr.ib(default="")
    ui_language: str = attr.ib()
    username: str = attr.ib()
    embeddings: Dict[str, List[float]] = attr.ib(default={})
    experiment_conditions: Dict[str, str] = attr.ib()
    user_id: str = attr.ib(default="")

There is an opensearch index of JeevesDocuments. When you are given a user's natural language query could you please convert it into a comma separated list of filters in Lucene Query Parser Syntax
and return the target topic of query in one or two words.

Please do not include words like opinions or reviews in the target topic

Please note that the only options for data_source are Twitter, JIRA, Zendesk, and AppFigures

Please note that shake_to_report_category can take four different values
    - EXTERNAL: documents are those that come from external shake-to-report
      testers, i.e. beta users.
    - INTERNAL: documents are those that come from internal shake-to-report
      testers, i.e. Duolingo employees (also known as duos).
    - NON_STR_EXTERNAL: documents are not associated with shake-to-report and
      originate from somewhere outside Duolingo, i.e. customer service reports
    - NON_STR_INTERNAL: documents are not associated with shake-to-report and
      originate from somewhere inside Duolingo, i.e. Jira.

Please format your response like:

Filters: <filter>, <filter>, <filter>
Target topic: <target topic>
"""

TARGET_TOPIC_THRESHOLD = 0.77


@registry.bind(
    ai_completions_dal=registry.reference(AICompletionsDAL),
)
class SentimentManager:
    def __init__(self, ai_completions_dal: AICompletionsDAL):
        self.ai_completions_dal = ai_completions_dal

    def filter_documents_using_topic(
        self, documents_list: List[JeevesDocument], target_topic: str
    ) -> List[JeevesDocument]:
        """
        Use cosine similarity to determine which documents match the target topic
        """
        target_embedding = self.ai_completions_dal.request_embedding(target_topic)
        docs_on_topic = []
        for document in documents_list:
            doc_embedding = document.embeddings[GPT_EMBEDDING_MODEL]
            similarity = calc_cosine_similarity(target_embedding, doc_embedding)
            if similarity > TARGET_TOPIC_THRESHOLD:
                docs_on_topic.append(document)
        return docs_on_topic

    def get_query_parameters(self, user_prompt: str) -> Dict[str, Union[Dict[str, str], str]]:
        """
        Method that should get called for the GET /query_params route. Turns a natural-language user prompt
        into a set of filters and a topic to search documents for.
        """
        response = {}
        response_text = self.ai_completions_dal.ask(SYSTEM_PROMPT, user_prompt)
        if response_text is None:
            response["filters"] = {}
            response["topic"] = "anything"
            return response
        # Everything on the first line after 'Filters: ' is the filters and everything on the second line after
        # 'Target topic: ' is the topic
        else:
            filters_text, labels_text = response_text.split("\n")
            response["filters"] = self._clean_up_filters(filters_text)
            response["topic"] = labels_text.split("Target topic: ")[1]
            return response

    @classmethod
    def _clean_up_filters(cls, filters_text):
        """
        Helper method to convert GPT filter output into a dict
        """
        filters = {}
        filters_text = filters_text.split("Filters: ")[1]
        for lucene_filter in filters_text.split(",") if "," in filters_text else [filters_text]:
            name, value = lucene_filter.split(":")
            filters[name.strip(" ")] = value.strip(" ")
        return filters
