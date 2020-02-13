"""
A ticket can be assigned with multiple categories defined in this class.

TODO: Support more categories.

Lauren's spreadsheet has the following categoies:
 - Lesson freezing
 - Offline mode not working
 - No sound
 - "Could not connect to Duolingo"
 - Windows issue
 - Lost progress
 - Strengthen skills
 - Speaking challenge
 - Android update
 - iOS update
 - Images not appearing
 - Can’t access account
 - Audio
 - App is slow
 - App crashes
 - Fluency score
 - Can't access skill
 - Grading incorrectly
 - Streak loss
 - TTS
 - Unable to log in
 - Error
 - Schools
 - Progress quiz
 - Issue at end of lesson
 - Problem testing out
 - Can't download app
 - Can't access app
 - Progress is wrong
 - Notifications
 - Streak payment
 - Listen challenges
 - Timed practice
 - Other
 - Chatbot
 - Clubs
 - Bonus skills
 - Streak freeze
 - Can't join clubs
 - Clubs stream not showing
"""

from enum import Enum, auto


class CATEGORIES(Enum):
    """Duolingo Jeeves tag categories"""

    bug = auto()
    suggestion = auto()
    inappropriate_ad = auto()
