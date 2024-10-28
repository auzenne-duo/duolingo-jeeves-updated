import json
import sys
from datetime import datetime, timedelta, timezone

import duo_logging
from duolingo_base.config import Config

from jeeves import apply_registry, close_registry, register, registry as app_registry
from jeeves.dal.spike_index_interface import SpikeIndexDAL
from jeeves.lib.spike_detector import (
    SPIKE_EXCLUDE_WORDS_REGISTRY_KEY,
    SPIKE_LEMMA_STATS_REGISTRY_KEY,
    STR_SPIKE_LEMMA_STATS_REGISTRY_KEY,
    detect_spikes,
)
from jeeves.util.date_util import date_to_str, get_utc_today, str_to_date, yield_intermediate_dates
from jeeves.util.s3_client_and_bucket import get_s3_client_and_bucket

_config = Config.load_config()

_FORCE_SPIKE_REFRESH_FILE = "force_spike_refresh_flag"
_SPIKE_CALCULATOR_LOCK_FILE = "spike_calculator_lock"
_SPIKE_EXCLUDE_WORDS_FILE = "spike_exclude_words"
_SPIKE_LEMMA_STATS_FILE = "spike_lemma_stats"
_STR_SPIKE_LEMMA_STATS_FILE = "str_spike_lemma_stats"
_LOCK_TIMEOUT = 12


def force_recalculate_all_spikes() -> None:
    """
    Performs spike detection on all documents currently available, ignoring any
    existing spike data, and indexes the result into OpenSearch.

    To force this method to run on the next invocation of the spike worker,
    simply write a '1' to the file specified in _FORCE_SPIKE_REFRESH_FILE in the
    appropriate S3 bucket.
    """
    detect_spikes(dry_run=False)


def run_spike_worker(dry_run: bool) -> None:
    """
    Main method for the spike worker thread.
    Determines first if a forceful refresh of all spikes is necessary. If so,
    perform this forceful refresh and exit. If not necessary, perform spike
    detection incrementally.
    """
    s3_client, s3_bucket_name = get_s3_client_and_bucket()

    # Check if the lock file exists. If not, create it in an unlocked state.
    spike_lock_list = list(
        s3_client.yield_filenames(s3_bucket_name, path_prefix=_SPIKE_CALCULATOR_LOCK_FILE)
    )
    if not spike_lock_list:
        s3_client.upload(s3_bucket_name, _SPIKE_CALCULATOR_LOCK_FILE, "0")
    # If the lock file indicates the lock is held, immediately exit.
    is_lock_held = (
        s3_client.download(s3_bucket_name, _SPIKE_CALCULATOR_LOCK_FILE)
        .decode("utf-8")
        .startswith("1")
    )
    lock_summary = s3_client.get_object_summary(s3_bucket_name, _SPIKE_CALCULATOR_LOCK_FILE)
    is_lock_expired = datetime.now(timezone.utc) - lock_summary.last_modified > timedelta(
        hours=_LOCK_TIMEOUT
    )

    if is_lock_held and not is_lock_expired and not dry_run:
        print("Lock already held, exiting early")
        return
    if not dry_run:
        # Lock was not held, claim the lock.
        print("Grabbing lock")
        s3_client.upload(s3_bucket_name, _SPIKE_CALCULATOR_LOCK_FILE, "1")

    # Load list of exclude words
    spike_exclude_words_file_list = list(
        s3_client.yield_filenames(s3_bucket_name, path_prefix=_SPIKE_EXCLUDE_WORDS_FILE)
    )
    if spike_exclude_words_file_list:
        register(
            SPIKE_EXCLUDE_WORDS_REGISTRY_KEY,
            (
                s3_client.download(s3_bucket_name, _SPIKE_EXCLUDE_WORDS_FILE)
                .decode("utf-8")
                .split("\n")
            ),
        )
    else:
        register(SPIKE_EXCLUDE_WORDS_REGISTRY_KEY, [])

    # Load baseline lemma stats
    spike_lemma_stats_file_list = list(
        s3_client.yield_filenames(s3_bucket_name, path_prefix=_SPIKE_LEMMA_STATS_FILE)
    )
    if spike_lemma_stats_file_list:
        register(
            SPIKE_LEMMA_STATS_REGISTRY_KEY,
            json.loads(s3_client.download(s3_bucket_name, _SPIKE_LEMMA_STATS_FILE).decode("utf-8")),
        )
    else:
        register(SPIKE_LEMMA_STATS_REGISTRY_KEY, {"words": {}})

    str_spike_lemma_stats_file_list = list(
        s3_client.yield_filenames(s3_bucket_name, path_prefix=_STR_SPIKE_LEMMA_STATS_FILE)
    )
    if str_spike_lemma_stats_file_list:
        register(
            STR_SPIKE_LEMMA_STATS_REGISTRY_KEY,
            json.loads(
                s3_client.download(s3_bucket_name, _STR_SPIKE_LEMMA_STATS_FILE).decode("utf-8")
            ),
        )
    else:
        register(STR_SPIKE_LEMMA_STATS_REGISTRY_KEY, {"words": {}})

    try:
        # Quick check to see if we have any spikes
        min_max_spike_dates = app_registry(SpikeIndexDAL).get_min_and_max_spike_dates()
        have_any_spikes = bool(min_max_spike_dates["max"])

        # Check if the force refresh file is present, and create it if not
        force_check_list = list(
            s3_client.yield_filenames(s3_bucket_name, path_prefix=_FORCE_SPIKE_REFRESH_FILE)
        )
        if not force_check_list:
            s3_client.upload(s3_bucket_name, _FORCE_SPIKE_REFRESH_FILE, "0")
        refresh_flag_str = s3_client.download(s3_bucket_name, _FORCE_SPIKE_REFRESH_FILE).decode(
            "utf-8"
        )

        if refresh_flag_str.startswith("1") or not have_any_spikes:
            s3_client.upload(s3_bucket_name, _FORCE_SPIKE_REFRESH_FILE, "0")
            print("Forcefully recalculating all spike data", flush=True)
            force_recalculate_all_spikes()
            return

        # For incremental spike detection, determine for what date we most recently
        # saw a spike. Then, run spike detection for every date between that date
        # and today (inclusive on both sides). This will typically end up meaning
        # that we re-run spike detection for today's date multiple times throughout
        # the day, which is somewhat inefficient. A better solution would be to
        # store the last time spike detection was run and only query for documents
        # indexed since that time but that would require setting up semi-volatile
        # storage which I'm not willing to do right now since its critical that
        # spike detection be brought back online ASAP.
        most_recent_spike_date = str_to_date(min_max_spike_dates["max"])
        todays_date = get_utc_today().date()

        print(
            f"Running incremental spike detection for dates {date_to_str(most_recent_spike_date)} to {date_to_str(todays_date)}",
            flush=True,
        )
        for inter_date in yield_intermediate_dates(most_recent_spike_date, todays_date):
            detect_spikes(target_date=inter_date, dry_run=dry_run)
    finally:
        # Release the lock.
        # We use a `finally` clause for this in case we ctrl-c or otherwise kill
        # the process out of order.
        if not dry_run:
            print("Releasing lock")
            s3_client.upload(s3_bucket_name, _SPIKE_CALCULATOR_LOCK_FILE, "0")


if __name__ == "__main__":
    try:
        apply_registry(_config)
        dry_run = sys.argv[1] == "True" if len(sys.argv) > 1 else True
        run_spike_worker(dry_run)
    except Exception as e:
        print(f"Exception occurred while running spike worker: {e}", flush=True)
        duo_logging.capture_exception(sys.exc_info())
    finally:
        close_registry()
