"""
This module provides DAL for FAQ data.

FAQ URL:
    https://support.duolingo.com/hc/en-us/articles/<id>

For example, an FAQ https://support.duolingo.com/hc/en-us/articles/217005666 can be represented
as the following JSON:
    {
      "body": "<p>You can learn multiple languages at the same time and save your progress.
               If you accidentally changed your interface language to something you cannot
               understand, please check out the article <a href=\"https://support.duolingo.com/
               hc/en-us/articles/204644534\">My account is in a language I do not understand! How
               do I change it back?</a></p>\n<p>If you are simply looking to add or switch to
               a different Duolingo course, here's how to do it:</p>\n<p><strong>On the
               web</strong></p> ...",
      "label_names": [
        "language",
        "site language",
        "new language",
        "change",
        "mobile",
        "base language",
        "ios",
        "android"
      ],
      "name": "How do I switch my Duolingo course language?",
      "title": "How do I switch my Duolingo course language?",
      "url": "https://duolingotest.zendesk.com/api/v2/help_center/en-us/articles/217005666-How-do-
              I-switch-my-Duolingo-course-language-.json",
      "vote_sum": 0,
      "created_at": "2016-11-14T22:40:39Z",
      "source_locale": "en-us",
      "comments_disabled": true,
      "html_url": "https://support.duolingo.com/hc/en-us/articles/217005666-How-do-I-switch-my-
                   Duolingo-course-language-",
      "section_id": 200829784,
      "updated_at": "2016-11-17T22:11:34Z",
      "locale": "en-us",
      "vote_count": 0,
      "outdated_locales": [],
      "draft": false,
      "promoted": false,
      "position": 0,
      "author_id": 799032220,
      "outdated": false,
      "id": 217005666
    }
"""
import time

import requests

_LOCALE = 'en-us'

_URL_TEMPLATE = ('https://support.duolingo.com/api/v2/help_center/{locale}/'
                 'articles.json?page={page}&per_page=100')

class ZendeskFAQDAL(object):
    """
    A DAL that fetches FAQs by using Zendesk API.
    """

    def __init__(self):
        self.faqs = {}

    def _lazy_init(self):
        """
        Since it takes time to initialize, let us do it on demand. There are only 100+ FAQ so we
        can store them all in memory.
        """
        count = 1
        while True:
            url = _URL_TEMPLATE.format(locale=_LOCALE, page=count)
            response = requests.get(url)
            json_response = response.json()
            self.faqs.update({article['id']: article for article in json_response['articles']})
            if count == json_response['page_count']:
                break
            count += 1
            # Avoid rate-limiting
            time.sleep(1)

    def get_faqs(self):
        """
        Returns a dict from FAQ ID to FAQ JSON.
        """
        if not self.faqs:
            self._lazy_init()
        return self.faqs

    def get_faq_by_id(self, faq_id):
        """
        Returns a dict from FAQ ID to FAQ JSON.
        """
        if not self.faqs:
            self._lazy_init()
        return self.faqs[faq_id]

FAQDAL = ZendeskFAQDAL()
