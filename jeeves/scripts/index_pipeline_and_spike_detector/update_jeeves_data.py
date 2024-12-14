import sys
import time

import duo_logging  # type: ignore[import]

from jeeves import apply_registry, close_registry
from jeeves.lib.ticket_crawler import crawl_tickets

if __name__ == "__main__":
    apply_registry()
    try:
        start = time.time()
        crawl_tickets()
        print("=" * 100)
        print(f"Batch done in {(time.time() - start):.3f} sec.")
        print("=" * 100)
    except:
        duo_logging.capture_exception(sys.exc_info())
    finally:
        close_registry()
