"""
A library for detecting whether and which FAQ can satisfy the question asked in a ticket.
"""
from jeeves.dal.faqs import FAQDAL

# pylint: disable=fixme
# TODO(Lawrence): Find the threshold
_FAQ_SCORE_THRESHOLD = 0.5


def detect_faq(ticket):
    """
    Given a ticket, detect which FAQ can answer it (or can't answer).

    Suppose there is a Zendesk ticket ID 805633:
        "So I am unable to switch to another course/language. I appreciate you taking a look at
        this or offering me some solutions I can try. aTHANK YOU."

    This function is expected to return FAQ article ID 217005666:
        "How do I switch my Duolingo course language? You can learn multiple languages as the ..."

    Parameter:
        ticket<SupportTicket>: A SupportTicket object.

    Returns:
        An FAQ ID (int) if there is a relevant FAQ detected, otherwise None.
    """
    scored_faqs = [(score_faq(ticket, faq), faq) for faq in FAQDAL.get_faqs().values()]
    sorted_scored_faqs = sorted(scored_faqs, key=lambda pair: pair[0], reverse=True)
    (best_faq_score, best_faq) = sorted_scored_faqs[0]
    return best_faq["id"] if best_faq_score > _FAQ_SCORE_THRESHOLD else None


# pylint: disable=unused-argument
def score_faq(ticket, faq):
    """
    Returns a score [0, 1] that represents how likely the given faq can satisfy the user who
    submitted the ticket. (As an approximation, this will return similarity of text between ticket
    and faq).
    """
    # pylint: disable=fixme
    # TODO(Lawrence): Implement something simple to start with
    import random

    return random.random()
