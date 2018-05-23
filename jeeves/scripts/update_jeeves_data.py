import requests
import time

from jeeves.lib.spike_detector import run_spike_detector
from jeeves.lib.ticket_crawler import crawl_tickets

if __name__ == '__main__':
    start = time.time()
    num_tickets_added = crawl_tickets()
    if num_tickets_added > 0:
        run_spike_detector()
        # Reset cache on web server
        print(requests.get('https://jeeves.duolingo.com/api/1/init').content)
    print('=' * 100)
    print('Batch done in %.3f sec.' % (time.time() - start))
    print('=' * 100)
