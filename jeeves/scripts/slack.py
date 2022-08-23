import json
import os
import sys
from typing import List
from urllib import parse

import rollbar
from duolingo_base.config import Config
from requests import post
from requests.exceptions import RequestException

from jeeves import apply_registry, close_registry, registry as app_registry
from jeeves.dal.spike_index_interface import SpikeIndexDAL
from jeeves.manager.shakira_slack import SlackChannel
from jeeves.model.spike_categories import SpikeCategory
from jeeves.model.spike_word import SpikeWord
from jeeves.util.date_util import date_to_str, get_eastern_today, get_n_days_ago
from jeeves.util.error_util import SpikeReporterException, print_request_exception

_config = Config.load_config()
_config.apply_logging()
_config.apply_rollbar()

_JEEVES_URL = "https://jeeves.duolingo.com"

_SLACK_REPORT_LANG = "en"

_SLACK_API = "https://slack.com/api"
_SLACK_API_TOKEN = os.environ.get("SPIKE_REPORTER_SLACK_API_TOKEN")
_SPIKE_CATEGORY_TO_SLACK_CHANNELS = {
    SpikeCategory.EXTERNAL_NON_STR_SPIKES: [SlackChannel.BUG_TRIAGE, SlackChannel.JEEVES]
}
# Messages for every spike category will only be sent to this channel from the dev environment.
_DEV_SLACK_CHANNEL = SlackChannel.POST_TEST_RESULTS

# The name of the category to be used in the message sent to the Slack channel.
_SPIKE_CATEGORY_TO_SLACK_FRIENDLY_NAME = {
    SpikeCategory.EXTERNAL_NON_STR_SPIKES: "customer feedback"
}


def get_yesterdays_date():
    return date_to_str(get_n_days_ago(get_eastern_today(), 1))


def get_top_spikes_yesterday(spike_category: SpikeCategory) -> List[SpikeWord]:
    # We are unfortunately limited to four spikes because the Slack API
    # only allows 10 cells for section block fields, which means we can have
    # at most five rows with two columns, and we need one of those rows for the
    # column titles
    num_spikes_to_list = 4

    spikes_yesterday = list(
        app_registry(SpikeIndexDAL).yield_spikes_on_date(
            _SLACK_REPORT_LANG,
            get_yesterdays_date(),
            num_spikes_to_list,
            spike_category,
        )
    )
    return spikes_yesterday


def get_jeeves_analysis_query_params(spike_word: SpikeWord):
    category_query = SpikeCategory.get_jeeves_query_params_for_category(spike_word.spike_group)
    jeeves_query = category_query
    jeeves_query["q"] = spike_word.word
    jeeves_query["use-lemmas"] = "true"
    jeeves_query["spike-category"] = spike_word.spike_group.name
    return jeeves_query


def get_jeeves_analysis_url_for_spike_word(spike_word: SpikeWord):
    jeeves_query = get_jeeves_analysis_query_params(spike_word)

    jeeves_base_url = f"{_JEEVES_URL}/{spike_word.lang}/analysis"
    jeeves_url_params = "&".join(
        [f"{key}={parse.quote(value)}" for key, value in jeeves_query.items()]
    )

    return f"{jeeves_base_url}?{jeeves_url_params}"


def spike_to_fields_array(spike: SpikeWord):
    jeeves_analysis_url = get_jeeves_analysis_url_for_spike_word(spike)

    spike_word_link = f"<{jeeves_analysis_url}|{spike.word}>"
    return [
        {"type": "mrkdwn", "text": spike_word_link},
        {"type": "plain_text", "text": f"{spike.score:.1f}"},
    ]


def generate_slack_message(spike_category: SpikeCategory, top_spikes: List[SpikeWord]):
    if any([spike for spike in top_spikes if spike.spike_group != spike_category]):
        raise SpikeReporterException("Spike words are not in the same category.")

    plural_adjustment = "" if len(top_spikes) == 1 else "s"
    plural_adj_verb = "is" if len(top_spikes) == 1 else "are"
    message_header = f"*Here {plural_adj_verb} the top {len(top_spikes)} trending word{plural_adjustment} we saw in {_SPIKE_CATEGORY_TO_SLACK_FRIENDLY_NAME[spike_category]} for {get_yesterdays_date()}:*"
    header_block = {"type": "section", "text": {"type": "mrkdwn", "text": message_header}}

    message_body_fields = [
        {"type": "mrkdwn", "text": "*Word*"},
        {"type": "mrkdwn", "text": "*Spikiness*"},
    ]
    for spike in top_spikes:
        message_body_fields += spike_to_fields_array(spike)

    body_block = {"type": "section", "fields": message_body_fields}

    prepared_message = [header_block, body_block]

    return prepared_message


if __name__ == "__main__":
    apply_registry()
    try:
        url = f"{_SLACK_API}/chat.postMessage"
        headers = {
            "Authorization": f"Bearer {_SLACK_API_TOKEN}",
            "Content-Type": "application/json; charset=utf-8",
        }
        for spike_category, slack_channels in _SPIKE_CATEGORY_TO_SLACK_CHANNELS.items():
            top_spikes = get_top_spikes_yesterday(spike_category)
            if len(top_spikes) == 0:
                continue

            slack_message = generate_slack_message(spike_category, top_spikes)

            slack_channels = (
                [_DEV_SLACK_CHANNEL]
                if _config.get_nested(["environment"]) == "dev"
                else slack_channels
            )
            for slack_channel in slack_channels:
                data = {
                    "channel": slack_channel.channel_id,
                    "blocks": slack_message,
                }
                try:
                    r = post(url, headers=headers, data=json.dumps(data))
                    r.raise_for_status()
                except RequestException as e:
                    print_request_exception(e)
                    rollbar.report_exc_info(sys.exc_info())
    except:
        rollbar.report_exc_info(sys.exc_info())
    finally:
        close_registry()
