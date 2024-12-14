import sys
import time

import duo_logging  # type: ignore[import]

from jeeves import apply_registry, close_registry
from jeeves.lib.ticket_crawler import force_refresh_tickets

if __name__ == "__main__":
    apply_registry()
    try:
        start = time.time()
        force_refresh_tickets()
        print("=" * 100)
        print(f"Refresh done in {(time.time() - start):.3f} sec.")
        print("=" * 100)
    except:
        duo_logging.capture_exception(sys.exc_info())
    finally:
        close_registry()
