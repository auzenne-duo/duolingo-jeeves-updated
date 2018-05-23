from datetime import datetime
import numpy as np
import simplejson as json

from jeeves.model import JeevesObject
from jeeves.util.date_util import datetime_to_str


class JeevesJSONEncoder(json.JSONEncoder):

    def default(self, o):  # pylint: disable=E0202
        if isinstance(o, JeevesObject):
            return o.__serialize__()
        elif isinstance(o, np.integer):
            return int(o)
        elif isinstance(o, np.floating):
            return float(o)
        elif isinstance(o, np.ndarray):
            return o.tolist()
        elif isinstance(o, datetime):
            return '%s UTC' % datetime_to_str(o)
        else:
            return super().default(o)
