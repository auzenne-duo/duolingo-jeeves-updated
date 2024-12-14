import os
import sys
import time

import duo_logging  # type: ignore[import]

from jeeves import apply_registry, close_registry, registry as app_registry
from jeeves.manager.quality_report_manager import QualityReportManager

_SAVE_SNAPSHOTS = os.environ.get("SAVE_SNAPSHOTS", "false").lower() == "true"
_IS_DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"
_DRY_RUN_RECIPIENT = recipient if (recipient := os.environ.get("DRY_RUN_RECIPIENT")) else None


if __name__ == "__main__":
    apply_registry()
    try:
        start = time.time()
        app_registry(QualityReportManager).generate_reports(
            save_snapshots=_SAVE_SNAPSHOTS,
            is_dry_run=_IS_DRY_RUN,
            dry_run_recipient=_DRY_RUN_RECIPIENT,
        )
        print("=" * 100)
        print(f"Quality Reports done in {(time.time() - start):.3f} sec.")
        print("=" * 100)
    except Exception as exc:
        duo_logging.capture_exception(sys.exc_info())
        raise exc
    finally:
        close_registry()
