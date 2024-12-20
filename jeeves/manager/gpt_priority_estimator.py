from __future__ import annotations

import json
import re
from dataclasses import dataclass

from duolingo_base.util import registry

from jeeves.dal.ai_completions_dal import AICompletionsDAL
from jeeves.model.jira_priorities import JiraPriority
from jeeves.model.jira_ticket_text import (
    REQ_DESCRIPTION,
    REQ_TITLE,
    JiraTicketText,
)

# The expected field names of the JSON response object
RESP_PRIORITY = "priority"
RESP_REASON = "reason"

SYSTEM_PROMPT = f"""
You are part of a quality analytics pipeline at Duolingo that helps employees to automatically triage Jira tickets.
When employees "shake" their device to report a bug, feature request, design issue, or some other feedback, they
fill out a form providing a "{REQ_TITLE}" (a brief summary) and "{REQ_DESCRIPTION}", which are converted into a Jira
ticket. Your job is to assign a priority to the ticket based on the textual content of the report and explain your
reasoning in 10 words or fewer. Sometimes, tickets will have only "{REQ_TITLE}" and no "{REQ_DESCRIPTION}", and that's
acceptable. You can just give your best judgment based on the information provided.

Respond with a JSON object containing only two string fields:
- "{RESP_PRIORITY}": The priority of the ticket (only "Highest", "High", "Medium", "Low", "Lowest", or "Unprioritized").
- "{RESP_REASON}": A brief justification for the priority assigned in "{RESP_PRIORITY}" in 10 words or fewer.

Use the following rubric to assign priorities:
- Highest: Feature rollout blocked until the bug is fixed. Should be a release blocker and resolved before rolling out
  the release. Patch no matter what. For example: Blocking, crashing, stuck: should probably trigger highest; serious
  PII or COPPA issues. Examples:
  - {REQ_TITLE}: Video call broke voice recognition? {REQ_DESCRIPTION}:
  - {REQ_TITLE}: only one node in daily refresh. {REQ_DESCRIPTION}: see screenshot
- High: Feature rollout blocked until the bug is fixed. May not block a release, but will need fixed within a week (or
  for the next release). For example: Learner blocking experiences with a work around, soft crashing, really gnarly
  visual bug, bad experiences. Potential buzzword: slow
  - {REQ_TITLE}: Phone gets stuck in ad. {REQ_DESCRIPTION}:
  - {REQ_TITLE}: Stuck on grey screen in lesson after exiting EMA purchase flow. {REQ_DESCRIPTION}:
  - {REQ_TITLE}: Lesson did not load. {REQ_DESCRIPTION}: When the lesson started nothing showed up, it was all white.
  - {REQ_TITLE}: No streak reward. {REQ_DESCRIPTION}: Saw an alert on the streak page. Clicking it I got a 3x XP boost
    for 900 day streak. I never got the XP boost and don't have one active now
  - {REQ_TITLE}: Video call not working. {REQ_DESCRIPTION}: I was able to do video call once and it crashed during
    session end, specifically from streak session end into friend streak session end, and now I am unable to do it
  - {REQ_TITLE}: Warning sign for losing streak after extending. {REQ_DESCRIPTION}: I just earned back my streak but
    the warning sign is still on top of my streak.
  - {REQ_TITLE}: [via Jeeves] No Audio. {REQ_DESCRIPTION}: 在做听力挑战时音频即使开到最大声都没有声音
  - {REQ_TITLE}: [via Jeeves] Listening Challenge - no audio. {REQ_DESCRIPTION}: 听写题音频缺失我怎么完成？而且还必须做完，
    循环出现，没法继续
  - {REQ_TITLE}: [via Jeeves] Music bug cannot continue. {REQ_DESCRIPTION}: Music section 1 unit 7. How am I supposed
    to compete 1 more lesson before continuing if there's no lesson available to do? ?!?
- Medium: Should be resolved before rollout, but can be resolved in further iterations if shipping a feature MVP. This
  could also block a feature if need be. Should not block a release. Should ideally be resolved within 1-3 months.
  For example: Poor alignment, cut off assets, small screen issues, content issues, localization bugs
  - {REQ_TITLE}: Texts go out of textbox. {REQ_DESCRIPTION}:
  - {REQ_TITLE}: clicking on an ad and going back results in blank screen. {REQ_DESCRIPTION}: I turned on Don't Keep
    Activities. Then I clicked on an ad (see video) Then I went back to the app. The screen was completely blank and
    non interactive.
  - {REQ_TITLE}: my feed is empty apart from friend suggestions. {REQ_DESCRIPTION}:
  - {REQ_TITLE}: World character image is missing from exercise. {REQ_DESCRIPTION}:
  - {REQ_TITLE}: Got the friends quest completed notification twice. {REQ_DESCRIPTION}: After finishing a path lesson I
    got a friends quest completion notification and all the screens but I did not get the +5 monthly quest credit.
    After closing and reopening I did a match madness and at the end I got another friends quest completion
    notification - including the +5 quest credit.
  - {REQ_TITLE}: Status bar no longer hidden on iPad? {REQ_DESCRIPTION}: (seems to not be visible in bug reporting
    screenshots but the status bar is no longer hidden on iPad, and occludes the progress bar…)
- Low: The feature can be shipped with low, but a plan should be in place to address via further iterations or a grease
  week. For example: Small visual bugs, bugs related to copysolidate.
  - {REQ_TITLE}: practice hub visibility weird. {REQ_DESCRIPTION}: Normally I don't see practice hub because I'm early
    in the path, but I can get there by tapping on "start video call" in the max dashboard, and then the tab disappears
    when I navigate away
  - {REQ_TITLE}: Tap tokens are very small. {REQ_DESCRIPTION}:
  - {REQ_TITLE}: Lily pronounces mmm as em em em. {REQ_DESCRIPTION}: A few times in my video call, Lily started her
    response with something like "eme eme eme". Based on the transcript I think she may be saying hmmm like it's an
    acronym and saying the letter M in Spanish three times. Super confusing.
  - {REQ_TITLE}: My perfect streak is longer than 8 weeks. {REQ_DESCRIPTION}: This says I've kept a perfect streak for
    8 weeks. But it's been much longer than that. I haven't used a streak freeze since November 2023.
  - {REQ_TITLE}: I have the widget already. {REQ_DESCRIPTION}: I have the widget so this shop shouldn't appear
  - {REQ_TITLE}: Small Hearts Count. {REQ_DESCRIPTION}: Is it me or is the hearts count, number three, smaller than it
    used to be.
  - {REQ_TITLE}: Heart option is really large. {REQ_DESCRIPTION}:
  - {REQ_TITLE}: Typefill polish - can we make the input field a bit smaller? It feels huge. {REQ_DESCRIPTION}: I know
    there are bigger changes needed for our keyboard but a simple place to srart
  - {REQ_TITLE}: Ad looks low resolution, looks fuzzy. {REQ_DESCRIPTION}:
- Lowest: Lowest bugs are issues that likely will never be resolved, may need to be closed as won't do. For example:
  Mostly visual nitpicks, rare edge cases. Examples:
  - {REQ_TITLE}: Animation after sharing sentence is glitchy. {REQ_DESCRIPTION}: Low prio since it is barely
    noticeable, but after sharing a sentence the entire challenge animated back in weirdly. I will attach a video.
  - {REQ_TITLE}: Minimized title bar when scrolling. {REQ_DESCRIPTION}: I would expect the title in the title bar to
    match the header (Food and Shopping), rather than say Roleplays again
- Unprioritized: Not enough context to determine the priority. For example: if the ticket refers to an image
  or a video but provides no context about the issue, or vague descriptions like "Fix this" or "Is this a bug?",
  or alternatively tickets that clearly aren't bug reports, like "Just testing!" or "Placeholder to grab logs"
"""


@dataclass
class GPTPriorityResponse:
    """
    The response from GPT containing the priority and reason for a Jira ticket.
    """

    priority: JiraPriority
    reason: str

    @classmethod
    def from_json(cls, json_str: str) -> GPTPriorityResponse:
        # Sanitize all control characters from JSON string before parsing
        json_str = re.sub(r"[\x00-\x1F\x7F-\x9F]", " ", json_str)
        data = json.loads(json_str)

        priority_resp = (
            JiraPriority.get_enum_from_string(data[RESP_PRIORITY])
            if data.get(RESP_PRIORITY)
            else JiraPriority.UNPRIORITIZED
        )

        return cls(
            priority=priority_resp if priority_resp else JiraPriority.UNPRIORITIZED,
            reason=data[RESP_REASON] if data.get(RESP_REASON) else "",
        )


@registry.bind(
    ai_completions_dal=registry.reference(AICompletionsDAL),
)
class GPTPriorityEstimator:
    def __init__(self, ai_completions_dal: AICompletionsDAL) -> None:
        self.ai_completions_dal = ai_completions_dal

    def estimate_priority(self, ticket: JiraTicketText) -> GPTPriorityResponse:
        """
        Given a title and description of an admin user's Shake-to-Report Jira ticket,
        ask GPT to estimate the priority of the ticket.

        Parameters:
            ticket: A `JiraTicketText` object representing a Jira ticket written by a Duo.

        Returns a `GPTPriorityResponse` instance containing GPT's assessment of the priority for this ticket
            as well as the reason it chose this priority.
        """
        if not ticket:
            raise ValueError("Cannot generate a priority for an undefined ticket.")

        # Ask ai-completions-backend to give a priority.
        response_text = self.ai_completions_dal.ask(
            system_prompt=SYSTEM_PROMPT,
            use_json_mode=True,
            user_prompt=ticket.to_yaml(),
        )
        return GPTPriorityResponse.from_json(response_text)
