"""
Contains a dictionary listing features and synonyms by Area > Team.
When an addition to this dictionary gets merged to master, the deploy job will automatically create
Features in Jira for the new additions.

Format:
{
    "Area": {
        "Team": {
            "Feature": ["Synonym"],
        },
    },
}

Notes:
- Feature names and synonyms are /not/ case-sensitive.
- The detector will match on substrings, so "notifications" will detect the term "notification".
- This also means that "question" will detect the term "quest" if quest is included as a synonym.

If you rename a feature on Jira, you must (1) update the feature name in this file, and (2) let the
team in charge of Jeeves know that their documents have to be refreshed.
"""

JIRA_FEATURES = {
    "Growth": {
        "China": {
            "China Compliances": [],
            "WeChat": ["wechat registration", "wechat login", "wechat sharing"],
            "Cantonese": [],
        },
        "Connections": {
            "Avatar Builder": ["avatar creator"],
            "Contact Sync": ["contact"],
            "DuoNews": ["duo news", "news"],
            "Feed Tab": [
                "kudos feed",
                "feature card",
                "nudge on feed",
                "gifting on feed",
                "sharing sentence to feed",
                "share sentence to feed",
                "share to feed",
            ],
            "Follow Suggestions": [
                "follow suggestion",
                "friend suggestion",
                "friend recommendation",
            ],
            "Friends": ["friend", "invite"],
            "Friends on Path": ["friends in path"],
            "Friends Quest": [
                "partner",
                "nudge",
                "say hi",
            ],
            "Kudos": ["congrats", "high five"],
            "Profile": [],
            "Profile Completion": [],
            "User Search": [],
        },
        "Onboarding": {
            "Onboarding": ["new user", "on boarding", "funboarding"],
            "Placement Test": [],
            "Course picker": ["course chooser", "language drawer", "flag", "flagship"],
        },
        "Priority Markets": {
            "Resurrected user experiences": ["surr", "resurrected", "reactivated"],
            "Registration": ["sign up"],
            "Login / Logout": ["login", "log in", "logout", "log out", "sign in", "sign out"],
        },
        "Retention": {
            "Streak": ["streak challenge", "vip", "society"],
            "Streak freeze / repair": ["streak freeze", "streak repair"],
            "Practice reminders / notifications": ["reminder", "notification"],
            "Early Bird / Night Owl Chests": ["early bird", "night owl"],
            "Lesson complete session end": ["complete"],
            "In-lesson Items (skip, retry)": ["skip", "retry", "in lesson item"],
            "Widget": [],
        },
        "Time Spent Learning": {
            "Achievements": ["achievement"],
            "Leaderboards": ["leaderboard", "tournament", "league", "context"],
            "Daily Quests": ["quests", "daily quest"],
            "Daily Goal": [],
            "Lesson Races": ["race"],
            "Monthly Goal": ["month"],
            "XP boost": ["double xp", "2x"],
            "Quests Tab": [],
        },
        "Virality": {
            "In-app sharing": ["sharing", "share", "share card", "rewarded sharing"],
            "Year in Review": [],
        },
        "None": {},
    },
    "Learning R&D": {
        "Experimental AI": {
            "Snips": [],
        },
        "Generated Sessions": {
            "Generated sessions": [],
            "Smart tips": ["smart tip"],
        },
        "Grading": {
            "Grading issue": [
                "grading",
                "Did not earn XP",
                "Didn't receive XP",
                "Did not receive XP",
            ],
        },
        "Advanced Monolingual English Experience": {
            "AMEE": ["monolingual"],
        },
        "New Writing Systems": {
            "Character Bingo": [
                "drawing",
                "tracing",
                "Session type: alphabet_lesson",
                "*session type*: alphabet_lesson",
            ],
            "Transliteration": [],
        },
        "Story Product": {
            "Stories": ["story"],
        },
        "Speech Lab": {
            "World character voice": [
                "voice",
                "tts voice",
                "junior voice",
                "zari voice",
                "lin voice",
                "bea voice",
                "oscar voice",
                "lily voice",
                "character voice",
            ],
            "Mouth animation": [
                "mouth animations",
                "visemes",
                "lip synch",
                "lip synching",
                "synchronization",
            ],
        },
        "None": {},
        "Path": {
            "Path": [
                "course",
                "level up",
                "home page",
                "home tab",
                "tree",
                "trophy",
                "trophies",
                "unit complete",
                "unit review",
            ],
            "Guidebook": [],
            "Path Sections": ["sections"],
            "Skill tree migration": ["course update"],
        },
    },
    "Learning Scaling": {
        "None": {
            # Lesson content and TTS issues go to Slack, not Jira
        },
    },
    "Monetization": {
        "Super Packaging": {
            "Ads / rewarded ads": ["ads"],
            "Super": [],
            "Hearts / Unlimited Hearts": [
                "heart",
            ],
            "Shop items": [],
            "New Years Promo": [],
        },
        "Poseidon": {
            "In-app purchases": ["shop"],
            "Ramp-up challenge": ["ramp up", "ramp-up"],
            "Gems / Lingots": ["gem", "lingot"],
            "Hard mode": [],
            "Match madness": [],
        },
        "Gold": {
            "Explain my Answer": [],
            "Role Play": ["roleplay", "role-play"],
            "Max": [],
        },
        "Super Features": {
            "Side Quests": ["side quest"],
            "Mistakes inbox": [],
            "Practice Hub": [],
            "Family plan": [],
            "Legendary": ["Legendarize"],
        },
    },
    "New Initiatives": {
        "Schools": {
            "Schools": [],
        },
    },
    "Product Quality": {
        "Delight": {
            "Callouts": [
                "callout",
                "call-out",
                "spotlight",
                "tool tip",
                "hint",
                "popout",
                "popover",
            ],
            "Settings": ["toggle", "admin", "menu", "account"],
            "World characters": [
                "world character",
                "character animation",
                "lily",
                "zari",
                "lin",
                "junior",
                "oscar",
                "eddy",
                "bea",
                "vikram",
                "lucy",
                "miguel",
                "face",
                "eye",
                "arm",
                "leg",
            ],
            "Animations": ["animat", "motion", "moving", "rive"],
            "Password Reset": [
                "reset password",
                "reset my password",
                "change password",
                "change my password",
            ],
            "Top Bar Navigation": ["toolbar", "tool bar", "stat bar", "stats bar"],
            "Course Switching": [
                "course pick",
                "course selection",
                "language pick",
                "language selection",
                "switching courses",
                "switching languages",
            ],
            "Mid-lesson animations / Duo": ["duo coach", "encouragement"],
            "Shake-to-report": ["shakira", "bug report", "shake to report"],
            "Offline support": ["prefetch", "offlin", "zombie", "airplane"],
            "DuoShorts": ["duo shorts"],
        },
        "None": {
            "Progress Bar": [],
            "Grading Ribbon": [
                "grading message",
                "incorrect drawer",
                "correct drawer",
                "incorrect bottom sheet",
                "correct bottom sheet",
                "grading drawer",
            ],
            "Incorrect XP Awarded": ["wrong xp"],
            "Challenge layout issues": [
                "exercise",
                "question",
                "problem",
                "speech bubble",
                "speaking bubble",
                "tap token",
                "token",
                "word bank",
            ],
            "General performance issues": [
                "crash",
                "error",
                "freeze",
                "frozen",
                "slow",
                "lag",
                "latency",
                "jank",
                "loading",
                "session bundle",
                "4xx",
                "5xx",
            ],
        },
        "Many": {
            "App startup": ["startup", "restart"],
        },
    },
    "None": {
        "None": {
            "Feature request / feedback": [],
            "Other": [],
        },
    },
    "Many": {
        "Many": {
            "Localization": ["translation", "string"],
            "Drawers / home messages": ["drawer", "home message"],
            "Session end screens": [
                "session end card",
                "session end message",
                "session end page",
                "session end screen",
                "session end slide",
                "SE card",
                "SE message",
                "SE page",
                "SE screen",
                "SE slide",
            ],
        },
    },
}

JIRA_FEATURES_REGISTRY_KEY = "jira_features"

JIRA_FEATURES_DESCRIPTIONS = {
    "Challenge layout issues": "Problems with format of elements in an exercise, such as overlapping tokens, text in incorrect location, missing prompts, etc.",
    "General performance issues": "App crashes, 4xx/5xx errors, freezes, slowness, etc.",
    "Progress Bar": "Issues with the progress bar at the top of a lesson.",
}

JIRA_FEATURES_DESCRIPTIONS_REGISTRY_KEY = "jira_features_descriptions"

SESSION_END_SCREEN_TO_FEATURE = {
    "sessionComplete": "Lesson complete session end",
    "completion_screen": "Lesson complete session end",
    "streak_extended": "Streak",
    "daily_quest_reward": "Daily Quests",
    "variable_chest_reward": "Daily Quests",
    "monthly_challenge_progress": "Monthly Goal",
    "streakExtended": "Streak",
    "doubleChestGemReward": "Daily Quests",
    "dailyQuestComplete": "Daily Quests",
    "league_rank_increase": "Leaderboards",
    "leaderboardRankIncreaseSmall": "Leaderboards",
    "new_streak_challenge_offer": "Streak",
    "interstitial_ad": "Ads / rewarded ads",
    "leaderboardMoveUpPrompt": "Leaderboards",
    "dailyQuestFirst": "Daily Quests",
    "juicy_native_ad": "Ads / rewarded ads",
    "monthly_goal_progress": "Monthly Goal",
    "monthlyGoal": "Monthly Goal",
    "daily_quest_passed_fifty_percent": "Daily Quests",
    "storyComplete": "Path",
    "early_bird_reward": "Early Bird / Night Owl Chests",
    "heart_refilled_vc": "Hearts / Unlimited Hearts",
    "ramp_up_end": "Ramp-up challenge",
    "monthlyChallengeComplete": "Monthly Goal",
    "achievementUnlocked": "Achievements",
    "rampUpSessionEndPromo": "Ramp-up challenge",
}

SESSION_END_SCREEN_TO_FEATURE_REGISTRY_KEY = "session_end_screen_to_feature"
