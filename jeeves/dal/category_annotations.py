class AbstractCategoryAnnotationDAL(object):

    def bulk_save_annotations(self, ticket_annotations):
        pass

    def get_annotations(self, ticket_id):
        pass


class SpreadSheetCategoryAnnotationDAL(object):

    def __init__(self):
        self._cache = None

    def _lazy_init(self):
        # TODO(Hideki): Read from Google Spreadsheet DB.
        self._cache = {}

    def bulk_save_annotations(self, ticket_annotations):
        if self._cache is None:
            self._lazy_init()
        for ticket_annotation in ticket_annotations:
            print(ticket_annotation['ticket_id'], ticket_annotation['category_labels'])
            self._cache[ticket_annotation['ticket_id']] = ticket_annotation['category_labels']
            # TODO(Hideki): Write to Google Spreadsheet DB.
        return {}

    def get_annotations(self, ticket_id):
        if self._cache is None:
            self._lazy_init()
        return self._cache.get(ticket_id, [])


class DatabaseCategoryAnnotationDAL(object):

    def bulk_save_annotations(self, ticket_annotations):
        pass

    def get_annotations(self, ticket_id):
        pass


CategoryAnnotationDAL = SpreadSheetCategoryAnnotationDAL()
