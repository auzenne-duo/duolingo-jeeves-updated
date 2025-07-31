"""
AI Query Manager for handling queries from different pages with context-specific prompts.
"""

import logging
import re
from enum import Enum
from typing import Optional

from duolingo_base.util import registry

from jeeves.dal.ai_completions_dal import AICompletionsDAL
from jeeves.resources.zendesk_tags import ZENDESK_TAGS

LOG = logging.getLogger(__name__)


class QuerySource(Enum):
    """Enumeration of possible query sources."""

    ISSUE_DISCOVERY = "issue_discovery"
    TIME_SERIES_ANALYZER = "time_series_analyzer"
    UNKNOWN = "unknown"


@registry.bind(ai_completions_dal=registry.reference(AICompletionsDAL))
class AIQueryManager:
    """Manager for handling AI queries with context-specific prompts."""

    def __init__(self, ai_completions_dal: AICompletionsDAL):
        self.ai_completions_dal = ai_completions_dal

    def _get_system_prompt(self, source: QuerySource) -> str:
        """Get the appropriate system prompt based on the query source."""
        if source == QuerySource.ISSUE_DISCOVERY:
            return """You are an AI assistant that translates natural language queries into OpenSearch query strings for issue discovery and bug analysis.

Your task is to convert user queries into optimized OpenSearch query syntax using these formats:
- Boolean operators: AND, OR with parentheses for grouping
- Regular expressions: /pattern/ for word variations (e.g., /crash(ing|ed|es)/)
- Exact phrases: "exact phrase" for multi-word sequences
- Include/exclude: +required -excluded

IMPORTANT:
- Do NOT use field searches (field:"value") as you don't know the available field names.
- Do NOT include platform terms (android, ios, web) in your response as these are handled separately.

Focus on issue-related terms and patterns:
- Error conditions: /crash(ing|ed|es)/ OR /freez(e|ing|es)/ OR /stuck|broken|fail(ed|ing)/
- User sentiment: /(disappoint|frustrat|annoy)(ed|ing)/ OR terrible OR horrible OR worst
- Problem reporting: /bug|issue|problem|error/ OR "doesn't work" OR "not working"

Examples:
User: "Find crashes related to login"
Response: /crash(ing|ed|es)/ AND (login OR /sign.?in/ OR authentication)

User: "Show me payment issues on android"
Response: (payment OR /pay(ing|ment)|purchase|billing/) AND (/fail(ed|ing)|error|problem|issue/)

Respond only with the OpenSearch query string, no explanations."""

        elif source == QuerySource.TIME_SERIES_ANALYZER:
            return """You are an AI assistant that translates natural language queries into OpenSearch query strings for time series analysis and trend identification.

Your task is to convert user queries into optimized OpenSearch query syntax using these formats:
- Boolean operators: AND, OR with parentheses for grouping
- Regular expressions: /pattern/ for word variations (e.g., /slow(er|ing|ness)/)
- Exact phrases: "exact phrase" for multi-word sequences
- Include/exclude: +required -excluded

IMPORTANT:
- Do NOT use field searches (field:"value") as you don't know the available field names.
- Do NOT include platform terms (android, ios, web) in your response as these are handled separately.

Focus on temporal and trend-related patterns:
- Performance issues: /slow(er|ing|ness)/ OR lag OR delay OR /freez(e|ing|es)/
- User feedback trends: I (hate OR "don't like") OR love OR /(disappoint|frustrat)(ed|ing)/
- Feature requests: (please (include OR add)) OR /lack(ing|s)/ OR limited OR suggestion
- Temporal indicators: /(recent|new|latest)/ OR "after update" OR /yesterday|today|week|month/

Examples:
User: "Show trends in app slowness"
Response: /slow(er|ing|ness)/ OR lag OR delay OR /freez(e|ing|es)/ OR unresponsive

User: "Find feedback about the latest update on ios"
Response: (latest (update OR version)) OR "last update" OR /recent.*update/ OR "after update"

User: "Look for refund requests over time"
Response: /refund(ed)?/ OR "money back" OR /return.*money/ OR /cancel.*subscription/

Respond only with the OpenSearch query string, no explanations."""

        else:  # UNKNOWN or fallback
            return """You are an AI assistant that translates natural language queries into OpenSearch query strings for software analytics and monitoring.

Convert user queries into OpenSearch syntax using:
- Boolean operators: AND, OR with parentheses
- Regular expressions: /pattern/ for variations
- Exact phrases: "phrase" for sequences
- Include/exclude: +required -excluded

IMPORTANT:
- Do NOT use field searches (field:"value") as you don't know the available field names.
- Do NOT include platform terms (android, ios, web) in your response as these are handled separately.

Respond only with the OpenSearch query string, no explanations."""

    def _detect_source_from_query(self, query: str) -> QuerySource:
        """
        Attempt to detect the source page from query content.
        This is a fallback when source is not explicitly provided.
        """
        query_lower = query.lower()

        # Keywords that suggest Issue Discovery page
        issue_keywords = [
            "issue",
            "bug",
            "error",
            "problem",
            "failure",
            "crash",
            "defect",
            "incident",
            "report",
            "duplicate",
            "priority",
        ]

        # Keywords that suggest Time Series Analyzer page
        time_keywords = [
            "trend",
            "time",
            "over time",
            "spike",
            "increase",
            "decrease",
            "pattern",
            "seasonal",
            "weekly",
            "daily",
            "monthly",
            "temporal",
            "chart",
            "graph",
            "series",
            "timeline",
            "historical",
        ]

        issue_score = sum(1 for keyword in issue_keywords if keyword in query_lower)
        time_score = sum(1 for keyword in time_keywords if keyword in query_lower)

        if time_score > issue_score and time_score > 0:
            return QuerySource.TIME_SERIES_ANALYZER
        elif issue_score > 0:
            return QuerySource.ISSUE_DISCOVERY
        else:
            return QuerySource.UNKNOWN

    def _detect_and_add_zendesk_tag_filters(self, query: str, ai_response: str) -> str:
        """
        Detect Zendesk tag mentions in the original query and add tag filters to the AI response.
        Handles spaces in user queries that correspond to underscores in tag names.

        Args:
            query: The original user query
            ai_response: The AI-generated query string

        Returns:
            Enhanced query string with tag filters if detected
        """
        query_lower = query.lower()
        tag_filters = []

        # Check for tag mentions in the query
        for tag in ZENDESK_TAGS:
            # Create variations of the tag to match against
            tag_lower = tag.lower()
            tag_with_spaces = tag_lower.replace("_", " ")

            # Check for exact matches (both underscore and space versions)
            if tag_lower in query_lower or tag_with_spaces in query_lower:
                tag_filters.append(f'tags:"{tag}"')

        # If we found tag mentions, enhance the AI response
        if tag_filters:
            if len(tag_filters) == 1:
                # Single tag: add as AND condition
                enhanced_response = f"({ai_response}) AND {tag_filters[0]}"
            else:
                # Multiple tags: add as OR condition for tags
                tag_condition = " OR ".join(tag_filters)
                enhanced_response = f"({ai_response}) AND ({tag_condition})"

            LOG.info(f"Enhanced query with tag filters: {tag_filters}")
            return enhanced_response

        return ai_response

    def _detect_and_add_platform_filter(self, query: str, ai_response: str) -> str:
        """
        Detect platform mentions in the original query and add platform filters to the AI response.

        Args:
            query: The original user query
            ai_response: The AI-generated query string

        Returns:
            Enhanced query string with platform filters if detected
        """
        query_lower = query.lower()
        platform_filters = []

        # Define platform patterns to detect
        platform_patterns = {
            "web": r"\bweb\b",
            "android": r"\bandroid\b",
            "ios": r"\bios\b",
        }

        # Check for platform mentions in the query
        for platform, pattern in platform_patterns.items():
            if re.search(pattern, query_lower):
                # Capitalize platform name for the filter (except 'iOS' which should be 'iOS')
                if platform == "ios":
                    platform_name = "iOS"
                elif platform == "android":
                    platform_name = "Android"
                else:  # web
                    platform_name = "Web"

                platform_filters.append(f'platform:"{platform_name}"')

        # If we found platform mentions, enhance the AI response
        if platform_filters:
            if len(platform_filters) == 1:
                # Single platform: add as AND condition
                enhanced_response = f"({ai_response}) AND {platform_filters[0]}"
            else:
                # Multiple platforms: add as OR condition for platforms
                platform_condition = " OR ".join(platform_filters)
                enhanced_response = f"({ai_response}) AND ({platform_condition})"

            LOG.info(f"Enhanced query with platform filters: {platform_filters}")
            return enhanced_response

        return ai_response

    def process_query(self, query: str, source: Optional[str] = None, max_tokens: int = 512) -> str:
        """
        Process an AI query with context-specific prompts.

        Args:
            query: The user's query text
            source: Optional source page identifier
            max_tokens: Maximum tokens for the response

        Returns:
            AIQueryResponse with the AI's response and detected source

        Raises:
            ValueError: If query is empty or invalid
            Exception: If AI service fails
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        # Determine query source
        if source:
            try:
                query_source = QuerySource(source.lower())
            except ValueError:
                LOG.warning(f"Unknown source '{source}', attempting to detect from query")
                query_source = self._detect_source_from_query(query)
        else:
            query_source = self._detect_source_from_query(query)

        # Get appropriate system prompt
        system_prompt = self._get_system_prompt(query_source)

        LOG.info(f"Processing AI query from source: {query_source.value}")

        # Call AI service
        try:
            ai_response = self.ai_completions_dal.ask(
                system_prompt=system_prompt,
                user_prompt=query,
                max_tokens=max_tokens,
                raise_exceptions=True,
            )

            if ai_response is None:
                raise Exception("AI service returned None response")

            # Apply platform detection and enhancement
            enhanced_response = self._detect_and_add_platform_filter(query, ai_response)

            # Apply Zendesk tag detection and enhancement
            enhanced_response = self._detect_and_add_zendesk_tag_filters(query, enhanced_response)

            return enhanced_response

        except Exception as e:
            LOG.error(f"Error processing AI query: {e!s}")
            raise e
