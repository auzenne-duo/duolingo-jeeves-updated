"""
A model representing a support ticket.
"""


class SupportTicket(object):

    classified_categories = {}

    def __init__(self, ticket_id, subject, description):
        # More meta data can be fetched using this ID.
        self.ticket_id = ticket_id

        self.subject = subject
        self.description = description
