"""
Exports Zendesk tickets.
We are using `incremental_export` API that allows us to get 1000 tickets at a time.
We have proper sleeps in each iteration in order to avoid being rate-limited.
API doc: https://developer.zendesk.com/rest_api/docs/core/incremental_export
"""

import datetime
import os
import requests
import simplejson as json
import time

from jeeves import data_directory

_ZENDESK_HOST = 'https://duolingotest.zendesk.com'
# _SEED_START = 1496275200  # 2017-06-01
# _END_TIME = 1498694400  # 2017-06-29

_USER = os.environ.get('ZENDESK_USER')
_PASSWORD = os.environ.get('ZENDESK_PASSWORD')

def downloadZendesk(startTime, endTime, directory=os.path.join(data_directory, 'zendesk')):
    next_url = '%s/api/v2/incremental/tickets.json?start_time=%s&end_time=%s' % (_ZENDESK_HOST, startTime, endTime)
    newFiles = []
    while True:
        r = requests.get(next_url, auth=(_USER, _PASSWORD))
        j = json.loads(r.text)
        try:
            next_url = j['next_page']
            with open(os.path.join(directory, 'tickets_%s.json' % j['end_time']), 'w') as f:
                f.write(r.text)
                newFiles.append(os.path.basename(f.name))
            print('Crawled until:', datetime.datetime.fromtimestamp(j['end_time']).strftime('%Y-%m-%d %H:%M:%S'))
            if j['count'] < 1000:
                break
            time.sleep(10)

        except KeyError:
            print(r.status_code)
            if r.status_code == 401:
                raise Exception('Authentication Error: %s' % r.text)
            print(r.text)
    return newFiles
