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
            "WeChat": [],
            "China Phone number": [],
            "China Compliances": [],
            "China Android Plus": [],
            "Year in Review": [],
            "Cantonese": [],
        },
        "Connections": {
            "Profile": [],
            "Referral": [],
            "Friends": ["friend", "invite", "contact"],
            "Friends Quest": [],
            "Kudos": ["congrats"],
            "DuoNews": ["duo news", "feed", "news"],
            "Friends Quest": [
                "partner",
                "nudge",
                "say hi",
            ],
        },
        "Onboarding": {
            "Onboarding": ["new user", "on boarding"],
            "Placement Test": [],
        },
        "Priority Markets": {
            "Welcome message": [],
            "Welcome back quest": [],
            "Course picker": ["course chooser", "language drawer", "flag", "flagship"],
            "What's app related": ["whatsapp", "whatsapp opt in"],
            "India phone number related": ["india"],
            "Social sign-in": ["apple sign in", "google sign in"],
            "Resurrected user experiences": ["surr", "resurrected", "reactivated"],
            "Registration": ["sign up"],
            "Login / Logout": ["login", "log in", "logout", "log out", "sign in", "sign out"],
        },
        "Retention": {
            "Streak": ["streak challenge"],
            "Streak Society": [],
            "Streak freeze / repair": ["streak freeze", "streak repair"],
            "Practice reminders / notifications": ["reminder", "notification"],
            "Early Bird / Night Owl Chests": ["early bird", "night owl"],
            "Lesson complete": ["complete"],
            "In Lesson Items": [],
        },
        "Time Spent Learning": {
            "Achievements": ["achievement"],
            "Leaderboards": ["leaderboard", "tournament", "league", "context"],
            "Daily Quests": ["quests", "daily quest"],
            "Daily Goal": [],
            "Monthly Goal": [],
            "XP boost": ["double xp", "2x"],
            "Quests Tab": [],
        },
        "Virality": {
            "In-app sharing": ["sharing", "share", "share card"],
            "Weekly progress report": ["weekly report", "progress report"],
        },
        "None": {
            "Next lesson ads": [],
        },
    },
    "Learning R&D": {
        "Learning Assesment": {
            "Checkpoint": ["section"],
            "Learning Assessment": ["learning quiz"],
            "Test Out": ["level skip"],
        },
        "Generated Sessions": {
            "Skill tree migration": ["course update"],
            "Crowns": [],
            "Decayed Skills": ["cracked skill", "guilded skill", "gilded"],
            "Generated sessions": [],
        },
        "Grading": {
            "Grading issue": [
                "grading",
                "Did not earn XP",
                "Didn't receive XP",
                "Did not receive XP",
            ],
        },
        "New Writing Systems": {
            "Character Bingo": ["drawing", "tracing"],
            "Transliteration": [],
            "Non-latin alphabet": [],
        },
        "Speaking": {
            "Audio Lessons": ["audio lesson", "podcast"],
            "Speech recognizer (in house)": [
                "speech recognition",
                "speech recognizer",
                "speech recogni",
            ],
        },
        "Story Product": {
            "Stories": ["story"],
            "Hoots": [],
            "Speaking exercises": ["speak challenge", "speak exercise"],
        },
        "Core v2": {
            "v2 feedback": [
                "ios_v2_dev: true",
                "*ios_v2_dev*: true",
                "android_v2_dev: true",
                "web_v2_dev: true",
                "path",
            ],
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
            ]
        },
        "None": {
            "Smart tips": ["smart tip"],
            "Tips": ["tip"],
            "Levels": ["level"],
        },
    },
    "Learning Scaling": {
        "None": {
            # Lesson content and TTS issues go to Slack, not Jira
        },
    },
    "Monetization": {
        "Plus": {
            "Ads / rewarded ads": ["ads"],
            "Plus": [],
            "Plus reward videos": [],
            "Hearts / Unlimited Hearts": [
                "heart",
            ],
            "Shop items": [],
            "New Years Promo": [],
            "Mistakes inbox": [],
            "Practice Hub": [],
            "Mastery / Progress quiz": ["mastery quiz", "progress quiz"],
            "Family plan": [],
            "Legendary": [],
            "Super": [],
            "Bookmarking": ["bookmark"],
        },
        "Poseidon": {
            "In-app purchases": ["shop"],
            "Ramp-up challenge": ["ramp up", "ramp-up"],
            "Gems / Lingots": ["gem", "lingot"],
            "Hard mode": [],
            "Match madness": [],
        },
        "Gold": {
            "Tutors": [],
            "Gold": [],
        },
    },
    "New Initiatives": {
        "Events": {
            "Events": ["overflow tab", "news feed"],
        },
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
            "Web home page": ["Landing page"],
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
            ],
            "Animations": ["animat", "motion", "moving"],
            "Password Reset": [
                "reset password",
                "reset my password",
                "change password",
                "change my password",
            ],
            "Skill Tree": ["course", "home page", "home tab", "tree"],
            "Top Bar Navigation": ["toolbar", "tool bar", "stat bar", "stats bar"],
            "Course Switching": ["course selection"],
            "Mid-lesson animations / Duo": ["duo coach", "encouragement"],
            "Dark mode messaging": [],
            "Shake-to-report": ["shakira", "bug report", "shake to report"],
            "Beta nag": ["beta message"],
            "Update nag": [],
            "E-mail verification": [
                "username",
                "password",
                "google",
                "facebook",
                "verif",
                "confirm",
            ],
            "Offline support": ["prefetch", "offlin"],
            "Web nag": [],
            "NPS": [],
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
                "word bank",
            ],
            "General performance issues": [
                "crash",
                "freeze",
                "frozen",
                "slow",
                "lag",
                "latency",
                "jank",
                "loading",
            ],
        },
        "Many": {
            "App startup": ["startup", "restart"],
        },
    },
    "None": {
        "None": {
            "Spam": [],
            "Feature request / feedback": [],
            "Other": [],
            "Writing system": [],
        },
    },
    "Many": {
        "Many": {
            "Localization": ["translation", "string"],
            "Dark mode": [],
            "Drawers / home messages": ["drawer", "home message"],
            "Session end screens": [
                "session end card",
                "session end message",
                "session end screen",
                "session end slide",
            ],
        },
    },
}

JIRA_FEATURES_REGISTRY_KEY = "jira_features"
