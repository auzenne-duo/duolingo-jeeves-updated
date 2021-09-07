import json
from datetime import datetime

from jeeves.util.date_util import datetime_to_str


class JeevesJSONEncoder(json.JSONEncoder):
    def default(self, o):  # pylint: disable=E0202
        if isinstance(o, datetime):
            return datetime_to_str(o)
        else:
            return super().default(o)
