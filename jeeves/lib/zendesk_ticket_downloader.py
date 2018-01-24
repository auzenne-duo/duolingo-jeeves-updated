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
from jeeves.lib.file_io import write_to_file

_ZENDESK_HOST = 'https://duolingotest.zendesk.com'

_USER = os.environ.get('ZENDESK_USER')
_PASSWORD = os.environ.get('ZENDESK_PASSWORD')


def download_tickets(start_time):
    next_url = '%s/api/v2/incremental/tickets.json?start_time=%s' % (_ZENDESK_HOST, start_time)
    new_files = []
    while True:
        r = requests.get(next_url, auth=(_USER, _PASSWORD))
        j = json.loads(r.text)
        try:
            file_name = 'tickets_%s.json' % j['end_time']
            write_to_file(r.text, file_name + '.gz',
                          dir_path=os.path.join(data_directory, 'zendesk'))
            new_files.append(os.path.basename(file_name))
            print('Crawled until:', datetime.datetime.fromtimestamp(j['end_time']).strftime('%Y-%m-%d %H:%M:%S'))
            if 'next_page' in j:
                next_url = j['next_page']
            if (j['count'] < 1000) or ('next_page' not in j) or (not next_url):
                break
            time.sleep(10)

        except KeyError:
            print(r.status_code)
            print('KeyError happened for URL=', next_url)
            print('Returned JSON', r.text)

    return new_files
