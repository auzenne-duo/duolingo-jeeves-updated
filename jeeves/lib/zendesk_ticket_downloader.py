"""
Exports Zendesk tickets.
We are using `incremental_export` API that allows us to get 1000 tickets at a time.
We have proper sleeps in each iteration in order to avoid being rate-limited.
API doc: https://developer.zendesk.com/rest_api/docs/core/incremental_export
"""

from collections import Counter
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

    urls = []
    while True:
        urls.append(next_url)
        # Break if same URL is requested for 5 times in a row
        if len(urls) > 5 and len(Counter(urls[-5:])) == 1:
            print('Stopped making request to zendesk after consecutive errors')
            break
        r = requests.get(next_url, auth=(_USER, _PASSWORD))
        j = json.loads(r.text)
        try:
            if 'error' in j:
                raise Exception('Error returned from Zendesk')
            file_name = 'tickets_%s.json' % j['end_time']
            write_to_file(
                r.text, file_name + '.gz', dir_path=os.path.join(data_directory, 'zendesk')
            )
            new_files.append(os.path.basename(file_name))
            print(
                'Crawled until:',
                datetime.datetime.fromtimestamp(j['end_time']).strftime('%Y-%m-%d %H:%M:%S')
            )
            if 'next_page' in j:
                next_url = j['next_page']
            else:
                break
            if j['count'] < 1000:
                break
            time.sleep(10)

        except Exception:
            print(r.status_code)
            print('KeyError happened for URL=', next_url)
            print('Returned JSON', r.text)

    return new_files
