"""
A model representing a support ticket.
"""


class SupportTicket(object):

    classified_categories = {}

    def __init__(self, ticket_id, date_time, subject, description, category_labels=None):
        """
        Parameters:
            ticket_id<int>: A zendesk ticket ID.
            subject<str>: A subject of the ticket.
            description<str>: A description of the ticket. This may include unstructured meta data.
            category_labels<collection<str>>: Gold standard labeled assinged by human annotator.
        """
        # More meta data can be fetched using this ID.
        self.ticket_id = ticket_id
        self.subject = subject
        self.description = description
        self.category_labels = category_labels

    def __repr__(self):
        def summarize(item):
            key, value = item
            if key == 'description' and len(value) > 30:
                return (key, value.replace('\n', ' ')[:30] + '...')
            else:
                return item
        variables = ', '.join('%s=%s' % summarize(item)
                              for item in vars(self).iteritems())
        return '%s(%s)' % (type(self).__name__, variables)
