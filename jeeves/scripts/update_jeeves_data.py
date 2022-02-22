import sys
import time

import rollbar
from duolingo_base.config import Config

from jeeves.lib.ticket_crawler import crawl_tickets

config = Config.load_config()
config.apply_logging()
config.apply_rollbar()


if __name__ == "__main__":
    try:
        start = time.time()
        crawl_tickets()
        print("=" * 100)
        print(f"Batch done in {(time.time() - start):.3f} sec.")
        print("=" * 100)
    except:
        rollbar.report_exc_info(sys.exc_info())
