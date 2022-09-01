import sys
import time

import rollbar
from duolingo_base.config import Config

from jeeves import apply_registry, close_registry
from jeeves.lib.ticket_crawler import force_refresh_tickets

config = Config.load_config()
config.apply_logging()
config.apply_rollbar()


if __name__ == "__main__":
    apply_registry()
    try:
        start = time.time()
        force_refresh_tickets()
        print("=" * 100)
        print(f"Refresh done in {(time.time() - start):.3f} sec.")
        print("=" * 100)
    except:
        rollbar.report_exc_info(sys.exc_info())
    finally:
        close_registry()
