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


Format:
{
    "Pillar": {
        "Area": {
            "Team": {
                "Feature": ["Synonym"],
            }
        }
    }
}

Notes:
- Feature names and synonyms are /not/ case-sensitive.
- The detector will match on substrings, so "notifications" will detect the term "notification".
- This also means that "question" will detect the term "quest" if quest is included as a synonym.

If you rename a feature on Jira, you must (1) update the feature name in this file, and (2) let the
team in charge of Jeeves know that their documents have to be refreshed.
"""

GROWTH = "Growth"
VIDEO_CALL = "Video Call"
JIRA_FEATURES = {
    "Monetization": {
        "no_area_monetization": {
            "Acquisition": {
                "Immersive subscriptions": ["immersive"],
                "Hearts / Unlimited Hearts": ["heart"],
                "Subscription hooks": [],
                "Super Upsell": [],
                "Family Plan": [],
                "Legendary": ["Legendarize"],
            },
            "Subscription Packaging": {
                "Purchase Flow": ["purchase page", "purchase screen", "purchase step"],
                "Duo on Path": [],
                "Super": [],
                "New Years Promo": [],
                "Student Plan": [],
                "Streak Society Promo": [],
                "Energy Retier": [],
            },
            "Crossgrades": {
                "Max Upsell": ["max purchase flow", "max crossgrade", "crossgrade"],
                "Crossgrades": ["upgrades", "downgrades"],
            },
            "Max": {
                "Mistakes Inbox": [],
                "Practice Hub": [],
                "Max": ["max user", "max", "max onboarding"],
                "Role Play": ["roleplay", "role-play"],
                "Words List": ["word list"],
                "Explain my Answer": ["EMA", "bad explanation", "wrong explanation", "explanation"],
            },
            "Energy": {
                "Gems / Lingots": ["gem", "lingot"],
                "Energy mechanism": ["energy"],
                "Hard mode": [],
                "Match madness": [],
                "Side Quests": ["side quest"],
                "In-app purchases": [
                    "shop",
                    "league repair",
                    "refill",
                    "timer boost",
                    "row blaster",
                ],
                "Shop items": [],
                "Ramp-up challenge": ["ramp up", "ramp-up"],
            },
            "Monetization Engine": {
                "Max Backend": [],
                "Purchasing": ["can't purchase"],
            },
            "Ads": {
                "Ads / rewarded ads": ["ads"],
            },
        },
    },
    GROWTH: {
        "International Growth": {
            "China": {
                "China Compliances": [],
                "China Android Super": [],
                "WeChat": ["wechat registration", "wechat login", "wechat sharing"],
            },
            "Momentum": {
                "Momentum": [],
            },
            "Re-Onboarding": {
                "Onboarding": ["new user", "on boarding", "funboarding"],
                "Course picker": ["course chooser", "language drawer", "flag", "flagship"],
                "Registration": ["sign up"],
                "Login / Logout": ["login", "log in", "logout", "log out", "sign in", "sign out"],
                "Resurrected user experiences": ["surr", "resurrected"],
                "Reonboarding": ["old user", "re onboarding", "reonboard"],
                "Year in Review": [],
            },
            "Score": {
                "Score": ["duolingo score", "scores"],
            },
        },
        "Area - Retention": {
            "Notifications": {
                "Notifications - Timing": ["notification", "practice reminder"],
            },
            "Reengagement": {
                "Notifications - Copy": ["reminder", "notification"],
                "Widget": [],
                "XP Happy Hour": [],
                "Live Activities": [
                    "live",
                    "activity",
                    "activities",
                    "lock screen",
                    "dynamic island",
                ],
            },
            "Retention": {
                "Achievements": ["achievement"],
                "Friend Streak": [
                    "friends streak",
                    "shared streak",
                    "streak partner",
                    "streak friend",
                    "title: Streak",
                    "FriendStreak",
                ],
                "Haptic Feedback": ["haptics", "vibrations", "buzz"],
                "Lesson complete session end": ["complete"],
                "Monthly Challenge": ["month"],
                "Streak": ["streak challenge", "vip", "society"],
                "Streak freeze / repair": ["streak freeze", "streak repair"],
            },
        },
        "no_area_growth": {
            "Social Engagement": {
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
                "Friends Clash": [
                    "clash",
                    "competition",
                    "friendzy",
                    "duel",
                    "battle",
                ],
                "Friends Quest": [
                    "partner",
                    "nudge",
                    "say hi",
                ],
                "Kudos": ["congrats", "high five"],
                "Profile": ["1pp", "3pp"],
                "Profile Completion": [],
                "User Search": [],
                "Tabs Redesign": [],
                "Early Bird / Night Owl Chests": ["early bird", "night owl"],
                "Leaderboards": ["leaderboard", "tournament", "league", "context"],
                "Daily Quests": ["quests", "daily quest"],
                "XP boost": ["double xp", "2x"],
                "Quests Tab": [],
                "Power Chests": ["timed chest"],
            },
            "Delight": {
                "In Lesson Delight": ["in lesson", "delight", "lightning", "flurry", "pulse"],
                "Hard Exercises": ["hard", "mislabel"],
                "Mid-lesson animations / Duo": ["duo coach", "encouragement"],
            },
        },
    },
    "Language Learning": {
        "Learning Experience": {
            "Intermediate English": {
                "SMEC": ["Intermediate English"],
                "Placement test": [],
                "Intermediate Mini Units IMU": [],
            },
            "Longform Content": {
                "DuoShorts": ["duo shorts"],
                "Stories": ["story"],
                "Pronunciation Bingo": [],
                "DuoRadio": [],
                "Adventures": [],
                "Immersive Speak": [],
            },
            "Unowned Learning": {
                "Generated sessions": [],
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
                "Smart tips": ["smart tip"],
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
                "Path Sections": ["daily refresh", "sections"],
                "Skill tree migration": ["course update"],
                "Character Bingo": [
                    "drawing",
                    "tracing",
                    "Session type: alphabet_lesson",
                    "*session type*: alphabet_lesson",
                ],
                "Layout Issues: Romaji/Furigana/Pinyin": ["Transliteration"],
                "Settings Issues: Romaji/Furigana/Pinyin": [],
            },
        },
        "Learning Scaling": {
            "GRID": {},
            "Translations": {
                "Translation Issue": [],
                "Grading issue": [],
            },
            "Automation Platform": {},
            "Curriculum Generation & Infrastructure": {},
            "Exercises": {},
        },
        VIDEO_CALL: {
            "Video Call Backend Foundations": {},
            "Video Call Experience": {"Video Call": ["facetime", "videocall"]},
            "Video Call Growth": {},
            "Video Call Scaffolding": {
                "Video Call Tab": [
                    "video-call tab",
                    "videocall tab",
                    "video call history",
                    "lily video message",
                ],
            },
        },
    },
    "New Subjects": {
        "Math": {
            "Math Curriculum Scaling": {
                "Math - LLM Content": [],
                "Math - Localization": [],
                "Math - Generated Sessions": [
                    "math content",
                    "math session",
                    "content accelerator",
                ],
                "Math": [],
            },
            "Math Navigation": {
                "Math - Visuals": ["math visual", "math interactive"],
                "Math - Match Madness": ["math match"],
                "Math - Puzzles & Games": ["math puzzles", "math paths", "CashDashNavigationVC"],
            },
            "Math Component Scaling": {
                "Math - Word Problems": ["word problems"],
                "Math - Life Skills": ["math stories"],
            },
        },
        "Music": {
            "Music Instruments": {
                "Music - Instrument Mode": ["instrument", "piano", "midi", "pitch"],
                "Music - Practice Tab": ["song library", "music library", "daily song"],
                "Music": [],
            },
            "Music Motivation": {},
            "Music Songs": {
                "Music - Licensed Songs": ["licensed"],
                "Music - Public Domain Songs": ["pd", "public"],
                "Music - Song Prep": ["prep"],
                "Music - World Character Songs": [],
            },
        },
        "no_area_new_subjects": {
            "Chess": {
                "Chess": ["edwin"],
            },
        },
    },
    "Platform": {
        "Design Accelerator": {
            "Design Systems": {
                "Progress Bar": [],
                "Grading Ribbon": [
                    "grading message",
                    "incorrect drawer",
                    "correct drawer",
                    "incorrect bottom sheet",
                    "correct bottom sheet",
                    "grading drawer",
                ],
                "Drawers / home messages": ["drawer", "home message"],
            },
            "Animation Accelerator": {
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
                "Rive": [],
            },
        },
        "Infrastructure Platform": {
            "App Stability and Performance": {
                "App startup": ["startup", "restart"],
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
            "Engineering Studio": {
                "Settings": ["toggle", "admin", "menu", "account"],
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
                "Shake-to-report": ["shakira", "bug report", "shake to report"],
                "Offline support": ["prefetch", "offline", "zombie", "airplane"],
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
    },
    "Other": {
        "Misc": {
            "Misc Team": {
                "Feature request / feedback": [],
                "Schools": [],
            }
        },
    },
}

JIRA_FEATURES_REGISTRY_KEY = "jira_features"

# Use this if you want to tag an entire project with a specific team
JIRA_TEAM_TO_PROJECT = {
    "Video Call Experience": ["VCCF", "EXAI"],
    "Video Call Backend Foundations": ["VCBF"],
    "Video Call Scaffolding": ["VCS"],
    "Video Call Growth": ["VCG"],
}

ALL_CUSTOM_PROJECTS = [proj for projects in JIRA_TEAM_TO_PROJECT.values() for proj in projects]

JIRA_FEATURES_DESCRIPTIONS = {
    "Achievements": "Claiming and viewing achievements in the profile page",
    "Ads / rewarded ads": "Problems with ads layout, audio, completion, etc.",
    "App startup": "Crashes or slowness on app startup",
    "Challenge layout issues": "Problems with format of elements in an exercise, such as overlapping tokens, text in incorrect location, missing prompts, etc.",
    "Character Bingo": "Issues specific to the Character Bingo exercise",
    "Course picker": "Issues with picking a course during onboarding",
    "Course Switching": "Issues with switching courses or languages",
    "Daily Quests": "Problems with daily quest progress, rewards, or related text/layout ",
    "Drawers / home messages": "For general drawer issues. If possible, choose a more specific feature.",
    "Duo on Path": "Issues with the animated Duo on path node feature for Super users",
    "DuoNews": "Issues with news cells in the Feed page",
    "Early Bird / Night Owl Chests": "Issues with the Early Bird or Night Owl chest rewards",
    "Explain my Answer": "Issues with the Explain my Answer tutor",
    "Family Plan": "Problems with the family plan (any tier)",
    "Feed Tab": "Issues on the Feed page such as Kudos, nudges, gifting",
    "Friend Streak": "Issues related to streaks shared with a friend (not personal streak)",
    "Friends": "Issues with Friends page, following people, friend updates",
    "Friends Quest": "Issues with the Friends Quest",
    "Friends Clash": "Issues with the Friends Clash",
    "General performance issues": "App crashes, 4xx/5xx errors, freezes, slowness, etc.",
    "Generated Sessions": "Problems within exercises such as missing tap tokens, broken buttons, etc. Not for content issues such as wrong translation.",
    "Grading Ribbon": "Issues with the grading ribbon that appears at the bottom of an exercise, specifically layout/formatting",
    "Grading issue": "Issues with the grading during lessons",
    "Translation Issue": "Issues with the translation",
    "Guidebook": "Bugs on a guidebook page",
    "Haptic Feedback": "Issues with missing haptics or haptics playing incorrectly",
    "Hard Exercises": "Use this if you think the exercise is mislabeled as hard",
    "Hard mode": "Problems with hard mode lessons specifically",
    "Immersive Speak": "Issues with the Immersive Speak session type",
    "Immersive subscriptions": "Any temporary subscription won from opening a chest on the path, does not include free trials",
    "In-app purchases": "Problems with items purchased with gems (row blaster, timer boosts, xp boost refills, league repairs, etc.)",
    "In Lesson Delight": "Issues with delightful animations for special in-lesson moments (progress bar pulse, grading ribbon lightning, session end XP flurry)",
    "Intermediate Mini Units IMU": "Issues with the flattened mini unit in B1+ content",
    "Kudos": "Problems with the 'Send congrats' drawer/celebrations on Feed page",
    "Layout Issues: Romaji/Furigana/Pinyin": "Issues with transliterations in the challenge",
    "Legendary": "Bugs with loading or doing legendary lessons",
    "Lesson complete session end": "Bugs for the card with a character animation and session stats. Not for general session end issues.",
    "Live Activities": "NOT for Session-related issues! Bugs for Live Activity *Notifications* on the Lock Screen (bad UI, not starting, lasting too long, deeplinking wrong, etc.)",
    "Max": "Anything with the Max subscriber experience. For purchasing Max via Video Call hooks, use 'Max Upsell'",
    "Max Upsell": "Anything related to 'Get Max' from Video Call upsells, Max purchase flow, and upgrading to Max from Super or Free, or upgrading from Max individual to Max Family Plan",
    "Mid-lesson animations / Duo": "Problems with the duo coach encouragement animations in between exercises",
    "Momentum": "Bugs with Momentum team features",
    "Monthly Challenge": "Bugs with the monthly challenge",
    "Music - Instrument Mode": "Problems with using a real instrument with the music course, either via pitch detection or MIDI.",
    "Music - Licensed Songs": "Problems with the song play experience for any licensed song.",
    "Music - Practice Tab": "Problems with the songs practice tab in the music course.",
    "Music - Public Domain Songs": "Problems with the song play experience for any public domain song.",
    "Music - Song Prep": "Problems with any song prep node.",
    "Music - World Character Songs": "Problems with the song play experience for any world character song.",
    "Notifications - Copy": "Bugs with the text or layout of the notification, or the notification settings.",
    "Notifications - Timing": "Bugs related to the timing, duplication, or frequency of notifications.",
    "Path": "Problems with the main path page, such as tiles not completing properly. Callouts on path fall under this feature.",
    "Path Sections": "Bugs with the section header, section cards, etc.",
    "Placement Test": "Issues with placement test in onboarding or when adding a new course",
    "Practice Hub": "Practice tab including speaking, listening, story, word, and personalized weekly practice",
    "Progress Bar": "Issues with the progress bar at the top of a lesson",
    "Purchasing": "Anything related to the actual act of purchasing, like wrong prices, refund problems, or purchasing failing",
    "Registration": "Bugs with profile creation flow after onboarding",
    "Session end screens": "General session end screen issues. If possible, use a more specific feature",
    "Settings": "Problems specifically on the settings page.",
    "Settings Issues: Romaji/Furigana/Pinyin": "Issues with transliteration settings not being obeyed",
    "Shake-to-report": "Problems with shake-to-report itself",
    "Shop items": "Bugs with the shop page, 'My Items' section of profile, purchasing shop items",
    "Side Quests": "Issues with the 'Rapid Review' exercises",
    "Smart Tips": "Bugs with exercises that start with 'Here's a tip:'",
    "Streak": "Incorrect or buggy streak number or calendar",
    "Streak freeze / repair": "Problems with using or equipping streak freeze or repair",
    "Streak Society Promo": "Anything related to the Streak Society Promotion subscription discount",
    "Student Plan": "Anything related to the Get Student Plan, Student Plan verification, or Student Plan Prices",
    "Super Upsell": "Includes Super hooks, tabs, and session end cards, but excludes Super ads and the purchase flow after entering the Super hook",
    "Tabs Redesign": "Redesigning the Profile, Feed, Leaderboard, and Quest tab for visual consistency.",
    "Purchase Flow": "Anything that happens after you enters the subscripton purchase flow",
    "Widget": "Problems with widget on home screen or widget reward",
    "World characters": "Missing or buggy world characters in lessons",
    "Video Call Tab": "Anything related to the Video Call tab, call history list, or Lily's video message",
    "Energy Retier": "Anything related to Energy Retier",
}

JIRA_FEATURES_DESCRIPTIONS_REGISTRY_KEY = "jira_features_descriptions"

SESSION_END_SCREEN_TO_FEATURE = {
    "sessionComplete": "Lesson complete session end",
    "completion_screen": "Lesson complete session end",
    "streak_extended": "Streak",
    "daily_quest_reward": "Daily Quests",
    "variable_chest_reward": "Daily Quests",
    "monthly_challenge_progress": "Monthly Challenge",
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
    "monthly_goal_progress": "Monthly Challenge",
    "monthlyGoal": "Monthly Challenge",
    "daily_quest_passed_fifty_percent": "Daily Quests",
    "storyComplete": "Path",
    "early_bird_reward": "Early Bird / Night Owl Chests",
    "heart_refilled_vc": "Hearts / Unlimited Hearts",
    "ramp_up_end": "Ramp-up challenge",
    "monthlyChallengeComplete": "Monthly Challenge",
    "achievementUnlocked": "Achievements",
    "rampUpSessionEndPromo": "Ramp-up challenge",
}

SESSION_END_SCREEN_TO_FEATURE_REGISTRY_KEY = "session_end_screen_to_feature"

JIRA_AREA_TO_PILLAR = {area: pillar for pillar, areas in JIRA_FEATURES.items() for area in areas}
JIRA_TEAM_TO_AREA = {
    team: area for _, areas in JIRA_FEATURES.items() for area in areas for team in areas[area]
}
JIRA_FEATURE_TO_TEAM = {
    feature: team
    for areas in JIRA_FEATURES.values()
    for teams in areas.values()
    for team, features in teams.items()
    for feature in features.keys()
}

# Maps from area/team name to a set of their features
AREA_TO_FEATURES = {
    area: {feature for features in teams.values() for feature in features}
    for pillar, areas in JIRA_FEATURES.items()
    for area, teams in areas.items()
}

PILLAR_TO_FEATURES = {
    pillar: {
        feature
        for areas in pillar_areas.values()
        for features in areas.values()
        for feature in features
    }
    for pillar, pillar_areas in JIRA_FEATURES.items()
}

TEAM_TO_FEATURES = {
    team: {feature for feature in features.keys()}
    for areas in JIRA_FEATURES.values()
    for teams in areas.values()
    for team, features in teams.items()
}

DEBUG_TYPE_TO_FEATURES = {
    "Max features": [
        "Explain my Answer",
        "Role Play",
    ]
}
DEBUG_TYPE_TO_FEATURES_REGISTRY_KEY = "debug_type_to_features"
