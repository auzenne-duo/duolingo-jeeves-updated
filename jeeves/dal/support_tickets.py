"""
DAL for zendesk support ticket dataset.
"""
from jeeves.lib.json_serializer import deserialize_tickets, serialize_tickets
from jeeves.lib.memcached_wrapper import MemcacheCompressionWrapper
from jeeves.model.products import Products
from jeeves.model.supported_languages import SUPPORTED_LANGUAGES


class MemcacheSupportTicketDAL(object):

    VERSION = 2
    TTL = 60 * 60 * 24 * 7  # 1 week

    def _get_cache_key(self, language=SUPPORTED_LANGUAGES.en, product=Products.LA):
        return 'tix:v%s:%s:%s' % (self.VERSION, language.name, product.name)

    def get_labeled_support_tickets(self, language=SUPPORTED_LANGUAGES.en, product=Products.LA):
        """
        Get a list of SupportTickets.

        Parameters:
            language (SUPPORTED_LANGUAGES): A language enum.
            product (Products): A product enum.
        """
        cache_key = self._get_cache_key(language=language, product=product)
        json_lines = MemcacheCompressionWrapper.get(cache_key)
        return deserialize_tickets(json_lines)

    def set_labeled_support_tickets(
        self, tickets, language=SUPPORTED_LANGUAGES.en, product=Products.LA
    ):
        """
        Set a list of SupportTickets.

        Parameters:
            tickets (list<SupportTicket>): A list of tickets.
            language (SUPPORTED_LANGUAGES): A language enum.
            product (Products): A product enum.
        """
        cache_key = self._get_cache_key(language=language, product=product)
        MemcacheCompressionWrapper.set(cache_key, serialize_tickets(tickets), self.TTL)


SupportTicketDAL = MemcacheSupportTicketDAL()
