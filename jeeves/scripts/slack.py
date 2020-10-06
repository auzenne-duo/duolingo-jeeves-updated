import json
import os
import requests

from jeeves.dal.elasticsearch_interface import ElasticDAL
from jeeves.util.date_util import get_eastern_today, get_n_days_ago, date_to_str


_SLACK_REPORT_LANG = "en"


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
            _SLACK_REPORT_LANG, get_yesterdays_date(), num_spikes_to_list
        )
    )
    return spikes_yesterday


def spike_to_fields_array(spike):
    spike_word_link = f"<https://jeeves.duolingo.com/{_SLACK_REPORT_LANG}/analysis?word={spike['word']}|{spike['word']}>"
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

    prepared_message = {"blocks": [header_block, body_block]}

    return prepared_message


if __name__ == "__main__":
    slack_post_url = os.environ.get("SLACK_POST_URL")
    slack_message = generate_slack_message(get_top_spikes_yesterday())
    requests.post(
        slack_post_url, data=json.dumps(slack_message), headers={"Content-Type": "application/json"}
    )
