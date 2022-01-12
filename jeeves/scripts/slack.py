import json
import os

from duolingo_base.config import Config
from requests import post
from requests.exceptions import RequestException

from jeeves.dal.elasticsearch_interface import ElasticDAL
from jeeves.manager.shakira_slack import SlackChannel
from jeeves.model.spike_categories import SpikeCategory
from jeeves.util.date_util import date_to_str, get_eastern_today, get_n_days_ago
from jeeves.util.error_util import print_request_exception

_config = Config.load_config()
_config.apply_logging()
_config.apply_rollbar()

_SLACK_REPORT_LANG = "en"

_SLACK_API = "https://slack.com/api"
_SLACK_API_TOKEN = os.environ.get("SPIKE_REPORTER_SLACK_API_TOKEN")
_SLACK_CHANNELS = (
    [SlackChannel.POST_TEST_RESULTS]
    if _config.get_nested(["environment"]) == "dev"
    else [SlackChannel.BUG_TRIAGE, SlackChannel.JEEVES]
)


def get_yesterdays_date():
    return date_to_str(get_n_days_ago(get_eastern_today(), 1))


def get_top_spikes_yesterday():
    # We are unfortunately limited to four spikes because the Slack API
    # only allows 10 cells for section block fields, which means we can have
    # at most five rows with two columns, and we need one of those rows for the
    # column titles
    num_spikes_to_list = 4

    spikes_yesterday = list(
        ElasticDAL.yield_spikes_on_date(
            _SLACK_REPORT_LANG,
            get_yesterdays_date(),
            num_spikes_to_list,
            SpikeCategory.EXTERNAL_NON_STR_SPIKES,
        )
    )
    return spikes_yesterday


def spike_to_fields_array(spike):
    spike_word_link = f"<https://jeeves.duolingo.com/{_SLACK_REPORT_LANG}/analysis?q={spike['word']}|{spike['word']}>"
    return [
        {"type": "mrkdwn", "text": spike_word_link},
        {"type": "plain_text", "text": f"{spike['score']:.1f}"},
    ]


def generate_slack_message(top_spikes):
    plural_adjustment = "" if len(top_spikes) == 1 else "s"
    plural_adj_verb = "is" if len(top_spikes) == 1 else "are"
    message_header = f"*Here {plural_adj_verb} the top {len(top_spikes)} trending word{plural_adjustment} we saw in customer feedback for {get_yesterdays_date()}:*"
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
    url = f"{_SLACK_API}/chat.postMessage"
    headers = {
        "Authorization": f"Bearer {_SLACK_API_TOKEN}",
        "Content-Type": "application/json; charset=utf-8",
    }
    slack_message = generate_slack_message(get_top_spikes_yesterday())

    for slack_channel in _SLACK_CHANNELS:
        data = {
            "channel": slack_channel.channel_id,
            "blocks": slack_message,
        }
        try:
            r = post(url, headers=headers, data=json.dumps(data))
            r.raise_for_status()
        except RequestException as e:
            print_request_exception(e)
