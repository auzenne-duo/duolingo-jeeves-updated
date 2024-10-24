import datetime
import json
import sys
from typing import List
from urllib import parse

import duo_logging
from duolingo_base.config import Config
from requests import post
from requests.exceptions import RequestException

from jeeves import apply_registry, close_registry, registry as app_registry
from jeeves.dal.spike_index_interface import SpikeIndexDAL
from jeeves.manager.shakira_slack import SlackChannel
from jeeves.model.slack_bot import SlackBot
from jeeves.model.spike_categories import SpikeCategory
from jeeves.model.spike_word import SpikeWord
from jeeves.util.date_util import date_to_str, get_eastern_today, get_n_days_ago
from jeeves.util.error_util import SpikeReporterException, print_request_exception

_config = Config.load_config()

_JEEVES_URL = "https://jeeves.duolingo.com"

_SLACK_REPORT_LANG = "en"

_SLACK_API = "https://slack.com/api"
_SPIKE_CATEGORY_TO_SLACK_CHANNELS = {
    SpikeCategory.EXTERNAL_NON_STR_SPIKES: [SlackChannel.JEEVES],
    SpikeCategory.EXTERNAL_STR_SPIKES: [SlackChannel.JEEVES],
}

# Keeps track of which bots posts to which channel
_SLACK_CHANNEL_TO_SLACK_BOT = {
    SlackChannel.JEEVES: [
        SlackBot.BETA_FEEDBACK_SPIKE_REPORTER,
        SlackBot.BUG_SPIKE_REPORTER,
        SlackBot.SOCIAL_TRENDS_SPIKE_REPORTER,
    ],
    SlackChannel.POST_TEST_RESULTS: [
        SlackBot.BETA_FEEDBACK_SPIKE_REPORTER,
        SlackBot.BUG_SPIKE_REPORTER,
        SlackBot.SOCIAL_TRENDS_SPIKE_REPORTER,
        SlackBot.SPIKE_REPORTER,
    ],
}

# Messages for every spike category will only be sent to this channel from the dev environment.
_DEV_SLACK_CHANNEL = SlackChannel.POST_TEST_RESULTS

# The name of the category to be used in the message sent to the Slack channel.
_SPIKE_CATEGORY_TO_SLACK_FRIENDLY_NAME = {
    SpikeCategory.EXTERNAL_NON_STR_SPIKES: "customer feedback",
    SpikeCategory.EXTERNAL_STR_SPIKES: "beta user feedback",
}

# Mapping from spike category to days of the week that spikes should be reported on
# where Monday is 1 and Sunday is 7. If a spike category is not in this mapping,
# spikes will not be reported on all days.
_SPIKE_CATEGORY_TO_REPORT_DAYS = {
    SpikeCategory.EXTERNAL_STR_SPIKES: [1, 5, 6, 7],  # Monday, Friday, Saturday, Sunday
}


def get_yesterdays_date():
    return date_to_str(get_n_days_ago(get_eastern_today(), 1))


def get_top_spikes_yesterday(spike_category: SpikeCategory) -> List[SpikeWord]:
    # This returns all spikes
    spikes_yesterday = list(
        app_registry(SpikeIndexDAL).yield_spikes_on_date(
            lang=_SLACK_REPORT_LANG,
            date_str=get_yesterdays_date(),
            num_spikes=None,
            spike_group=spike_category,
            only_bugs=False,
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

    spike_word_link = f"*<{jeeves_analysis_url}|{spike.word}>*"
    summary_line = "\n" + spike.summary if spike.summary else ""
    return [
        {"type": "mrkdwn", "text": f"{spike_word_link}{summary_line}"},
        {"type": "plain_text", "text": f"{spike.score:.1f}"},
    ]


def spike_sorter(spikes: List[SpikeWord], curr_spike_category: SpikeCategory):
    """
    For each bot prepare a set of spikes to be posted depending on the spike category and
    whether the spikes are a social media trend versus a bug.
    We are unfortunately limited to four spikes because the Slack API
    only allows 10 cells for section block fields, which means we can have
    at most five rows with two columns, and we need one of those rows for the
    column titles, so each bucket can only have four spikes.

    Return a dictionary with the bot's slack name as the key and the top four spikes in a list as the value
    """
    spike_buckets = {
        SlackBot.SPIKE_REPORTER.slack_name: spikes,
        SlackBot.BUG_SPIKE_REPORTER.slack_name: [],
        SlackBot.SOCIAL_TRENDS_SPIKE_REPORTER.slack_name: [],
        SlackBot.BETA_FEEDBACK_SPIKE_REPORTER.slack_name: spikes,
    }

    for spike in spikes:
        if spike.is_bug:
            spike_buckets[SlackBot.BUG_SPIKE_REPORTER.slack_name].append(spike)
        elif spike.is_social_trend:
            spike_buckets[SlackBot.SOCIAL_TRENDS_SPIKE_REPORTER.slack_name].append(spike)
    for bot in spike_buckets:
        spike_buckets[bot] = sorted(spike_buckets[bot], key=lambda x: x.score, reverse=True)[:4]

    # Only beta feedback bot posts beta feedback spikes
    if curr_spike_category == SpikeCategory.EXTERNAL_STR_SPIKES:
        spike_buckets[SlackBot.BUG_SPIKE_REPORTER.slack_name] = []
        spike_buckets[SlackBot.SOCIAL_TRENDS_SPIKE_REPORTER.slack_name] = []
    elif curr_spike_category == SpikeCategory.EXTERNAL_NON_STR_SPIKES:
        spike_buckets[SlackBot.BETA_FEEDBACK_SPIKE_REPORTER.slack_name] = []

    return spike_buckets


def generate_slack_message(
    spike_category: SpikeCategory, top_spikes: List[SpikeWord], spike_type_insert=""
):
    if any([spike for spike in top_spikes if spike.spike_group != spike_category]):
        raise SpikeReporterException("Spike words are not in the same category.")

    plural_adjustment = "" if len(top_spikes) == 1 else "s"
    plural_adj_verb = "is" if len(top_spikes) == 1 else "are"
    message_header = (
        f"*Here {plural_adj_verb} the top {len(top_spikes)} trending word{plural_adjustment} we saw "
        f"{spike_type_insert}in {_SPIKE_CATEGORY_TO_SLACK_FRIENDLY_NAME[spike_category]} for "
        f"{get_yesterdays_date()}:*"
    )
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
    apply_registry(_config)
    try:
        url = f"{_SLACK_API}/chat.postMessage"
        weekday = datetime.datetime.now().weekday()
        for spike_category, slack_channels in _SPIKE_CATEGORY_TO_SLACK_CHANNELS.items():
            if weekday not in _SPIKE_CATEGORY_TO_REPORT_DAYS.get(spike_category, range(7)):
                continue
            top_spikes = get_top_spikes_yesterday(spike_category)
            spikes_for_bots = spike_sorter(
                top_spikes, spike_category
            )  # Prepare spikes for each bot
            if len(top_spikes) == 0:
                continue

            slack_channels = (
                [_DEV_SLACK_CHANNEL]
                if _config.get_nested(["environment"]) == "dev"
                else slack_channels
            )  # Only post to the dev channel in the dev environment

            for slack_channel in slack_channels:
                for bot in _SLACK_CHANNEL_TO_SLACK_BOT[slack_channel]:
                    headers = {
                        "Authorization": f"Bearer {bot.api_token}",
                        "Content-Type": "application/json; charset=utf-8",
                    }
                    spikes_for_channel = spikes_for_bots[bot.slack_name]

                    if len(spikes_for_channel) != 0:
                        slack_message = generate_slack_message(
                            spike_category, spikes_for_channel, bot.spike_type_insert
                        )

                        data = {
                            "channel": slack_channel.channel_id,
                            "blocks": slack_message,
                        }
                        try:
                            print(
                                f"Posting to slack for {spike_category} in {slack_channel} by {bot.slack_name}"
                            )
                            r = post(url, headers=headers, data=json.dumps(data))
                            r.raise_for_status()
                        except RequestException as e:
                            print_request_exception(e, log_level="error")
    except:
        duo_logging.capture_exception(sys.exc_info())
    finally:
        close_registry()
