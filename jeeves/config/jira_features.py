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
        "Resurrection": {
            "Resurrected user experiences": ["surr", "resurrected", "reactivated"],
            "Registration": ["sign up"],
            "Login / Logout": ["login", "log in", "logout", "log out", "sign in", "sign out"],
        },
        "Reengagement": {
            "Practice reminders / notifications": ["reminder", "notification"],
            "Lesson complete session end": ["complete"],
            "Widget": [],
        },
        "Retention": {
            "Achievements": ["achievement"],
            "Early Bird / Night Owl Chests": ["early bird", "night owl"],
            "Streak": ["streak challenge", "vip", "society"],
            "Streak freeze / repair": ["streak freeze", "streak repair"],
        },
        "Time Spent Learning": {
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
        "Media Learning": {
            "DuoShorts": ["duo shorts"],
            "Stories": ["story"],
            "Pronunciation Bingo": [],
            "DuoRadio": [],
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
            "Words List": ["Word list"],
            "Legendary": ["Legendarize"],
        },
    },
    "New Initiatives": {
        "Schools": {
            "Schools": [],
        },
    },
    "New Subjects": {
        "Mega": {
            "Mega": ["app promo", "accelerator"],
        },
        "Math": {
            "Math": [],
        },
        "Music": {
            "Music": [],
        },
    },
    "Product Quality": {
        "Delight": {
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
    "Achievements": "Claiming and viewing achievements in the profile page",
    "Ads / rewarded ads": "Problems with ads layout, audio, completion, etc.",
    "AMEE": "Issues with Advanced Monolingual English Experience exercises",
    "App startup": "Crashes or slowness on app startup",
    "Cantonese": "Issues specific to the Cantonese course",
    "Challenge layout issues": "Problems with format of elements in an exercise, such as overlapping tokens, text in incorrect location, missing prompts, etc.",
    "Character Bingo": "Issues specific to the Character Bingo exercise",
    "Course picker": "Issues with picking a course during onboarding",
    "Course Switching": "Issues with switching courses or languages",
    "Daily Goal": "Issues with daily xp goal rewards, progress not being respected",
    "Daily Quests": "Problems with daily quest progress, rewards, or related text/layout ",
    "Drawers / home messages": "For general drawer issues. If possible, choose a more specific feature.",
    "DuoNews": "Issues with news cells in the Feed page",
    "Early Bird / Night Owl Chests": "Issues with the Early Bird or Night Owl chest rewards",
    "Explain my Answer": "Issues with the Explain my Answer tutor",
    "Family plan": "Problems with the Super family plan",
    "Feed Tab": "Issues on the Feed page such as Kudos, nudges, gifting",
    "Friends": "Issues with Friends page, following people, friend updates",
    "Friends Quest": "Issues with the Friends Quest",
    "General performance issues": "App crashes, 4xx/5xx errors, freezes, slowness, etc.",
    "Generated Sessions": "Problems within exercises such as missing tap tokens, broken buttons, etc. Not for content issues such as wrong translation.",
    "Grading issue": "Issues with answers not being accepted, wrong grading results",
    "Grading Ribbon": "Issues with the grading ribbon that appears at the bottom of an exercise, specifically layout/formatting",
    "Guidebook": "Bugs on a guidebook page",
    "Hard mode": "Problems with hard mode lessons specifically",
    "In-app purchases": "Problems with purchasing gems, row blaster, timer boosts, etc.",
    "In-app sharing": "Bugs with the share button or share card.",
    "Kudos": "Problems with the 'Send congrats' drawer/celebrations on Feed page",
    "Legendary": "Bugs with loading or doing legendary lessons",
    "Lesson complete session end": "Bugs specifically with the lesson complete session end card",
    "Mid-lesson animations / Duo": "Problems with the duo coach encouragement animations in between exercises",
    "Monthly Goal": "Bugs with monthly quest",
    "Mouth animation": "Problems with mouth visemes (lip synching)",
    "Other": "Please try to use a specific feature if possible.",
    "Path": "Problems with the main path page, such as tiles not completing properly. Callouts on path fall under this feature.",
    "Path Sections": "Bugs with the section header, section cards, etc.",
    "Placement Test": "Issues with placement test after onboarding or 'Jump Here' test in path",
    "Practice Hub": "Practice tab including speaking, listening, story, word, and personalized weekly practice",
    "Progress Bar": "Issues with the progress bar at the top of a lesson",
    "Registration": "Bugs with profile creation flow after onboarding",
    "Session end screens": "General session end screen issues. If possible, use a more specific feature",
    "Settings": "Problems specifically on the settings page.",
    "Shake-to-report": "Problems with shake-to-report itself",
    "Shop items": "Bugs with the shop page, 'My Items' section of profile, purchasing shop items",
    "Side Quests": "Issues with the 'Rapid Review' exercises",
    "Smart Tips": "Bugs with exercises that start with 'Here's a tip:'",
    "Streak": "Incorrect or buggy streak number or calendar",
    "Streak freeze / repair": "Problems with using or posessing streak freeze or repair",
    "Widget": "Problems with widget on home screen or widget reward",
    "World characters": "Missing or buggy world characters in lessons",
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
