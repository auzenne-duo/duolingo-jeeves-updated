"""
DAL for accessing category annotation data.

TODO: Implement a function that exports labeled dataset that machine learning libraries can use.
"""

import requests


class AbstractCategoryAnnotationDAL:
    def bulk_save_annotations(self, ticket_annotations):
        pass

    def get_annotations(self, ticket_id):
        pass


class SpreadSheetCategoryAnnotationDAL:
    _KEY = "AKfycbx6JvPzdYwV8Brd-aoxPuwDT8iItlA41fLRLWb4HRwvSMeh4Lg"
    _API_URL = f"https://script.google.com/macros/s/{_KEY}/exec"

    def __init__(self):
        self._cache = None

    def _lazy_init(self):
        response = requests.get(self._API_URL)
        # There may be duplicate ticket_id but newer row overwrites older one.
        self._cache = {ticket["ticket_id"]: ticket["category_labels"] for ticket in response.json()}

    def bulk_save_annotations(self, ticket_annotations):
        if self._cache is None:
            self._lazy_init()
        for ticket_annotation in ticket_annotations:
            print(ticket_annotation["ticket_id"], ticket_annotation["category_labels"])
            self._cache[ticket_annotation["ticket_id"]] = ticket_annotation["category_labels"]
        response = requests.post(self._API_URL, json=ticket_annotations)
        return {"ok": response.ok}

    def get_annotations(self, ticket_id):
        if self._cache is None:
            self._lazy_init()
        return self._cache.get(ticket_id, [])


class DatabaseCategoryAnnotationDAL:
    def bulk_save_annotations(self, ticket_annotations):
        pass

    def get_annotations(self, ticket_id):
        pass


CategoryAnnotationDAL = SpreadSheetCategoryAnnotationDAL()
