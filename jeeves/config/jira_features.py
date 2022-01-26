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
"""

JIRA_FEATURES = {
    "Growth": {
        "China": {
            "WeChat": [],
            "China Phone number": [],
            "Words list": [],
            "China Android Plus": [],
            "Year in Review": [],
        },
        "Connections": {
            "Profile": [],
            "Referral": [],
            "Friends": ["friend", "invite"],
            "Kudos": [],
        },
        "Onboarding": {
            "Onboarding": ["new user", "on boarding"],
            "Placement Test": [],
            "Registration": ["sign up"],
        },
        "Priority Markets": {
            "Welcome message": [],
            "Welcome back quest": [],
            "Course picker": ["course chooser", "language drawer", "flag"],
            "What's app related": [],
            "India phone number related": [],
            "Apple sign-in": ["social sign in"],
            "Resurrected user experiences": [],
            "Login / Logout": ["login", "log in", "logout", "log out", "sign in", "sign out"],
        },
        "Retention": {
            "Streak": [],
            "Streak freeze / repair": ["streak freeze", "streak repair"],
            "Monthly Goal": [],
            "Practice reminders / notifications": ["reminder", "notification"],
        },
        "Time Spent Learning": {
            "Achievements": ["achievement"],
            "Leaderboards": ["leaderboard", "tournament", "league", "context"],
            "Daily Quests": ["quests", "daily quest"],
            "Daily Goal": [],
            "XP boost": ["double xp"],
        },
        "Virality": {
            "In-app sharing": [],
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
            "Checkpoint": ["section"],
            "Learning Assessment": ["learning quiz"],
            "Test Out": ["level skip"],
        },
        "Learning Efficiency": {
            "Skill tree migration": ["course update"],
            "Crowns": [],
            "Course messaging": [],
        },
        "New Writing Systems": {
            "Character Bingo": ["drawing"],
            "Transliteration": [],
        },
        "Speaking": {
            "Pronunciation Review": ["speaking challenge"],
            "Audio Lessons": ["audio lesson", "podcast"],
            "Speech recognizer (in house)": ["speech recogni"],
        },
        "Stories Product": {
            "Stories": ["story"],
            "Hoots": [],
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
            "Ramp-up challenge": ["ramp up", "ramp-up"],
            "Gems / Lingots": ["gem", "lingot"],
            "Hard mode": ["challenge"],
        },
        "Sigma": {
            "Mistakes inbox": [],
            "Practice Hub": [],
            "Mastery / Progress quiz": ["mastery quiz", "progress quiz"],
            "Family plan": [],
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
                " lin ",
                " lin's",
                "junior",
                "oscar",
                " eddy",
                "bea",
                "vikram",
                "lucy",
                "miguel",
            ],
            "Animations": ["animat", "motion", "moving", "performance mode"],
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
            "Incorrect XP Awarded": [],
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
