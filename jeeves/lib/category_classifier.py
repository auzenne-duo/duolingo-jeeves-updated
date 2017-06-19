"""
A library for classifying tickets into categories.
"""
import re

from jeeves.model.categories import CATEGORIES
from jeeves.model.support_ticket import SupportTicket

class AbstractCategoryClassifier(object):

    def is_classifiable(self, description, category):
        """
        Runs a trained text classifier model to identify whether `description` can be classified as
        `category`.

        Parameters:
            description<str>: A ticket description.
            category<str>: One of categories of a ticket.

        Returns
            True or False
        """
        pass

    def get_categories_for_ticket(self, ticket):
        return {category for category in CATEGORIES
                if self.is_classifiable(ticket.description, category)}


class RuleBasedCategoryClassifier(AbstractCategoryClassifier):

    def is_classifiable(self, description, category):
        # Baseline 1
        if category == 'inappropriate_ad':
            return re.search(r'\b(ad)\b', description)
        elif category == 'streak_issue':
            return re.search(r'\b(streak)\b', description)


class SimpleMachineLearningBasedCategoryClassifier(AbstractCategoryClassifier):

    def is_classifiable(self, description, category):
        # Baseline 2
        pass


class SuperCoolMachineLearningBasedCategoryClassifier(AbstractCategoryClassifier):

    def is_classifiable(self, description, category):
        # Here goes an implementation that can beat the baselines.
        # Be careful about ROI -- time spent on implementing this may not justify improvement in accuracy
        # It's perfectly fine to use a simple model at the end.
        pass


if __name__ == '__main__':
    classifier = RuleBasedCategoryClassifier()
    ticket = SupportTicket(1, 'Hi', 'I saw a bad ad.')
    print classifier.get_categories_for_ticket(ticket)
