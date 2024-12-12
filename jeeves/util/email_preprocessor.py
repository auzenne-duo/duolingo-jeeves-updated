"""
A util for extracting meaningful body text from an email.

Example 1: email with reply part
```
Thanks for the invitation but this year I cannot afford going.

On 22 May 2018, at 01:59, Duolingo Community Team > wrote:
Duolingo Global Ambassador Summit 2018 RSVP
View this email in your browser.
```

Example 2: email with reply part
```
I will be unable to attend as it is in the middle of my school's exam period.
________________________________
From: Duolingo Community Team
Sent: Tuesday, May 22, 2018 12:58:47 AM
```

TODO: consider using 3rd party tool or machine learning (sequential tagging).
"""

import re

_CLOSING = re.compile(
    (
        "^(Best|Best Regards|Best wishes|Cheers|Kind regards|Regards|Sincerely|"
        "Sincerely yours|Thanks|Thank you|Thanks in advance|Yours sincerely)[,!]?$"
    ),
    re.IGNORECASE,
)

_QUOTE = re.compile(".+ (wrote|escribió|escreveu|a écrit|ha scritto)[ ]?:$")

_SEPARATOR = re.compile("^[_-]{25,}$")


def _is_below_junk(line):
    return _CLOSING.match(line) or _QUOTE.match(line) or _SEPARATOR.match(line)


def cleanup_email(body_text):
    lines = body_text.split("\n")
    pos = next((i for i, line in enumerate(lines) if _is_below_junk(line)), None)
    return "\n".join(lines[:pos])
