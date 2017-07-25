import numpy as np
import simplejson as json

from jeeves.model import JeevesObject

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
        else:
            return super().default(o)
