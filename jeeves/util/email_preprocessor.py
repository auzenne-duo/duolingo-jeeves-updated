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


def _is_below_junk(line):
    return (
        line.endswith('wrote:') or line.startswith('From:') or line.startswith('_' * 30)
        or line.startswith('-' * 30)
    )


def cleanup_email(body_text):
    lines = body_text.split('\n')
    pos = next((i for i, line in enumerate(lines) if _is_below_junk(line)), None)
    return '\n'.join(lines[:pos])
