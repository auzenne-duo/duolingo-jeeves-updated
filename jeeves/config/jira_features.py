"""
Contains a dictionary listing features and synonyms by Area > Team.

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
"""

JIRA_FEATURES = {
    "Growth": {
        "China": {
            "WeChat": [],
            "China Phone number": [],
            "Words list": [],
            "China Android Plus": [],
            "Year in Review": [],
            "In-app sharing": [],
        },
        "Connections": {
            "Profile": [],
            "Referral": [],
            "Friends": ["friend"],
            "Kudos": [],
        },
        "Globalization": {
            "CopyCAT": [],
        },
        "Onboarding": {
            "Onboarding screens": [],
            "Placement Test": [],
            "Registration": [],
        },
        "Opportunity Markets": {
            "Welcome message": [],
            "Welcome back quest": [],
            "Course picker": [],
            "What's app related": [],
            "India phone number related": [],
            "Apple sign-in": [],
            "Resurrected user experiences": [],
            "Login / Logout": ["login", "log in", "logout", "log out"],
        },
        "Retention": {
            "Streak": [],
            "Streak freeze / repair": ["streak freeze", "streak repair"],
            "Monthly goal": [],
            "Practice reminders / notifications": ["practice reminder", "notification"],
        },
        "Time Spent Learning": {
            "Achievements": ["achievement"],
            "Leaderboards": ["leaderboard"],
            "Quests": [],
            "Daily goal": [],
            "XP boost": [],
        },
        "None": {
            "Birdhouse audio room": [],
            "Next lesson ads": [],
        },
    },
    "Learning": {
        "Learning Efficiency": {
            "Decayed Skills": [],
        },
    },
    "Learning R&D": {
        "Learning Assesment": {
            "Checkpoint": [],
            "Learning Assessment": [],
            "Test Out": [],
        },
        "Learning Efficiency": {
            "Skill tree migration": [],
            "Crowns": [],
            "Course messaging": [],
        },
        "New Writing Systems": {
            "Character Bingo": [],
            "Transliteration": [],
        },
        "Speaking": {
            "Pronunciation Review": [],
            "Audio Lessons": ["audio lesson"],
        },
        "Stories Product": {
            "Stories": ["story"],
            "Hoots": [],
        },
        "None": {
            "Smart tips": ["smart tip"],
            "Tips": ["tip"],
            "Levels": [],
        },
    },
    "Learning Scaling": {
        "None": {
            # Lesson content and TTS issues go to Slack, not Jira
        },
    },
    "Monetization": {
        "Midas": {
            "Ads / rewarded ads": ["ads"],
            "Plus": [],
            "Plus reward videos": [],
            "Hearts / Unlimited Hearts": [
                "heart",
            ],
            "Flashcards": [],
            "Shop items": [],
            "New Years Promo": [],
        },
        "Poseidon": {
            "In-app purchases": [],
            "XP ramp up": [],
            "Gems / Lingots": ["gem", "lingot"],
            "Hard mode": [],
        },
        "Sigma": {
            "Mistakes inbox": [],
            "Practice Hub": [],
            "Mastery / Progress quiz": ["mastery quiz", "progress quiz"],
            "Plus Family Plan": [],
            "Legendary": [],
        },
    },
    "New Initiatives": {
        "Events": {
            "Events": [],
        },
        "Schools": {
            "Schools": [],
        },
    },
    "Product Quality": {
        "Delight": {
            "Callouts": ["callout"],
            "Settings": [],
            "World characters": ["world character"],
            "Animations": ["animation"],
            "Password Reset": [],
            "Skill Tree": [],
            "Top Bar Navigation": [],
            "Course Switching": [],
            "Mid-lesson animations / Duo": [],
            "Dark mode messaging": [],
            "Shake-to-report": [],
            "Beta nag": [],
            "Update nag": [],
            "E-mail verification": [],
            "Offline support": [],
            "Web nag": [],
            "NPS": [],
        },
        "None": {
            "Progress Bar": [],
            "Grading Ribbon": [],
            "Incorrect XP Awarded": [],
            "Challenge layout issues": [],
            "General performance issues": [],
        },
        "Many": {
            "App startup": [],
        },
    },
    "None": {
        "None": {
            "Spam": [],
            "Feature request / feedback": [],
            "Writing system": [],
        },
    },
    "Many": {
        "Many": {
            "Localization": [],
            "Dark mode": [],
            "Drawers / home messages": ["drawer", "home message"],
            "Session end screens": ["session end"],
        },
    },
}
