import os
import sys
from datetime import datetime, timedelta, timezone

import duo_logging  # type: ignore[import]

from jeeves import apply_registry, close_registry, registry as app_registry
from jeeves.dal.opensearch_interface import OpenSearchDAL
from jeeves.dal.spike_index_interface import SpikeIndexDAL
from jeeves.model.spike_word import SpikeWord
from jeeves.util.date_util import str_to_date
from jeeves.util.slack_util import SlackUtil

_DEFAULT_SLACK_CHANNEL_ID = "C0UDM7XA4"  # for #slack-test channel
_SLACK_CHANNEL_ID = os.environ.get("SLACK_CHANNEL_ID", _DEFAULT_SLACK_CHANNEL_ID)
_SLACK_API_TOKEN = os.environ.get("SLACK_API_TOKEN")


DATA_SOURCES_MAX_EXPECTED_AGE = {
    # Use larger stale threshold for AppFigures because we get them once for the whole day after they become available.
    "AppFigures": timedelta(days=3),
    "JIRA": timedelta(days=1),
    "Reddit": timedelta(days=2),
    "Zendesk": timedelta(days=2),
}

SPIKE_WORD_MAX_AGE = timedelta(days=2)


def get_latest_document(data_source: str) -> None:
    """
    Get the latest document from OpenSearch for the given data source.
    """
    query = {
        "size": 1,
        "sort": {"date_time": "desc"},
        "query": {"term": {"data_source": data_source}},
    }

    indexed_issues = app_registry(OpenSearchDAL).execute_arbitrary_query(query)
    return indexed_issues[0]


def get_latest_spike() -> SpikeWord:
    """
    Get the latest spike.
    """
    query = {"size": 1, "sort": {"date": "desc"}, "query": {"match_all": {}}}
    spikes = app_registry(SpikeIndexDAL).execute_arbitrary_query(query)
    return spikes[0]


if __name__ == "__main__":
    apply_registry()
    slack_obj = SlackUtil(slack_channel_id=_SLACK_CHANNEL_ID, slack_api_token=_SLACK_API_TOKEN)
    try:
        print("Checking spike detector")
        spike = get_latest_spike()
        print(f"Latest spike: {spike.word}; Creation time: {spike.date}")
        print(
            f"Difference between now and creation time: {datetime.now(timezone.utc).date() - str_to_date(spike.date)}. "
            f"Max expected age: {SPIKE_WORD_MAX_AGE}"
        )
        if datetime.now(timezone.utc).date() - str_to_date(spike.date) > SPIKE_WORD_MAX_AGE:
            msg = f"JEEVES WARNING: Spike data is stale! Latest spike: {spike.word}; Creation date: {spike.date}."
            if os.environ.get("BUILD_URL"):
                msg += f"See {os.environ.get('BUILD_URL')} for more info."
            slack_obj.send_slack_message(msg)
        print("Finished checking spike detector")

        for data_source, max_expected_age in DATA_SOURCES_MAX_EXPECTED_AGE.items():
            print(f"Checking {data_source}...")
            doc = get_latest_document(data_source)
            print(
                f"Latest {data_source} document: {doc.jeeves_uid}; Creation time: {doc.date_time}"
            )
            print(
                f"Difference between now and creation time: {datetime.now(timezone.utc) - doc.date_time}. Max expected age: {max_expected_age}"
            )
            if datetime.now(timezone.utc) - doc.date_time > max_expected_age:
                msg = f"JEEVES WARNING: {data_source} data is stale! Latest document: {doc.jeeves_uid}; Creation time: {doc.date_time}."
                if os.environ.get("BUILD_URL"):
                    msg += f"See {os.environ.get('BUILD_URL')} for more info."
                slack_obj.send_slack_message(msg)

        print("Finished checking data sources.")
    except:
        print("Unexpected error:", sys.exc_info())
        duo_logging.capture_exception(sys.exc_info())
    finally:
        close_registry()
