"""
A manager for providing a definition of a topic in the context of Duolingo.
"""

from duolingo_base.util import registry

from jeeves.dal.ai_completions_dal import AICompletionsDAL

REQ_TOPIC = "topic"
RESP_DESCRIPTION = "description"

TOPIC_DEFINITION_SYSTEM_PROMPT = f"""
You will be given a topic. Describe that topic in the context of Duolingo in 5-10 words. If you aren't sure just write the original topic.

Duolingo is a language-learning app that uses gamification to make learning fun and engaging.

The app has characters that help users learn new languages. These characters are animated and appear in the app's lessons. Here are the names of the characters and their descriptions:
    - Duo: the mascot of Duolingo, a green owl (Note that Duos plural refers to Duolingo employees)
    - Bea: ambitious, type-A go getter
    - Eddy: earnest, fitness-loving, single dad
    - Falstaff: opposite of Duo the owl, moody, lethargic, short-tempered
    - Junior: devious, fun-loving, son of Eddy
    - Lily: deadpan, emo teenage artist
    - Lin: laid-back, bohemian free spirit
    - Lucy: canny, vivacious, woman of the world, spy
    - Oscar: demanding teacher, impeccable aesthete, artist
    - Vikram: optimistic, open-hearted dreamer and baker
    - Zari: super-enthusiastic, excitable teen

A streak is the number of days in a row users have completed a lesson on Duolingo. Users can set their own daily XP target to reach their streak. If users don't do a lesson, users will have to
use a streak freeze or else they will lose their streak.

Leaderboards are a feature where users can compete in leagues. The leagues in order are Bronze, Silver, Gold, Sapphire, Ruby, Emerald, Amethyst, Pearl, Obsidian, and Diamond.

Friends quests are weekly challenges that users complete with one of their Duolingo friends.

Users get three daily quests each day. If they complete enough daily quests, they will get a badge for that month.

Gems are the virtual currency for all iOS, Android, and web users. Web users used to use lingots. Users will earn Gems or Lingots for completing lessons on Duolingo.
Typically users will earn gems when they complete Daily Quests.

Duolingo Stories are exercises focused on reading and listening comprehension. Duolingo characters will guide users through a series of events.

Users can lose Hearts by answering incorrectly too many times! Super users have unlimited hearts.

Super Duolingo is a subscription to Duolingo. Super users get unlimited hearts, no ads, mistakes review, and unlimited attempts at legendary challenges.

Duolingo Max is a subscription to Duolingo. Max users get all the benefits of Super Duolingo along with two new AI powered features: Explain My Answers and Roleplay.
Explain my Answers is where users can tap a button after certain exercise types and chat with Duo to get a simple explanation
on why their answer was right or wrong. Roleplay is where users can practice their conversation skills by texting back and forth with Duolingo characters in the app.

Family Plan is where a primary account manager can share a Duolingo subscription with up to 5 other users.

Input format:
{REQ_TOPIC}: <target topic>

Output format:
{RESP_DESCRIPTION}: <topic description>
"""


@registry.bind(
    ai_completions_dal=registry.reference(AICompletionsDAL),
)
class TopicDefinitionManager:
    def __init__(self, ai_completions_dal: AICompletionsDAL):
        self.ai_completions_dal = ai_completions_dal

    def get_topic_description(self, target_topic: str) -> str:
        """
        Use GPT to get a description of the target topic
        """
        response_text = self.ai_completions_dal.ask(
            TOPIC_DEFINITION_SYSTEM_PROMPT, f"{REQ_TOPIC}: {target_topic}"
        )
        return response_text.split(f"{RESP_DESCRIPTION}: ")[1]
