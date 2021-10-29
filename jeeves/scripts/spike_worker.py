from datetime import datetime, timedelta, timezone

from duolingo_base.config import Config
from duolingo_base.dal import s3

from jeeves.dal.elasticsearch_interface import ElasticDAL  # pylint: disable=E0401
from jeeves.lib.spike_detector import (  # pylint: disable=E0401
    split_beta_batches_and_run_detector,
    split_beta_batches_and_run_for_date,
)
from jeeves.model.supported_languages import SUPPORTED_LANGUAGES  # pylint: disable=E0401
from jeeves.util.date_util import get_utc_today  # pylint: disable=E0401
from jeeves.util.date_util import str_to_date, yield_intermediate_dates

_config = Config.load_config()
_config.apply_logging()
_config.apply_rollbar()

_FORCE_SPIKE_REFRESH_FILE = "force_spike_refresh_flag"
_SPIKE_CALCULATOR_LOCK_FILE = "spike_calculator_lock"
_LOCK_TIMEOUT = 12


def force_recalculate_all_spikes(s3_client: s3.S3Client, s3_bucket_name: str) -> None:
    """
    Performs spike detection on all documents currently available, ignoring any
    existing spike data, and indexes the result into Elasticsearch.

    To force this method to run on the next invocation of the spike worker,
    simply write a '1' to the file specified in _FORCE_SPIKE_REFRESH_FILE in the
    appropriate S3 bucket.
    """
    # By batching documents we can hopefully improve runtime, since spike
    # detection passes multiple documents to each ES mtermvectors command.
    document_batch = []
    _BATCH_TARGET_SIZE = 1000
    # It is assumed that one page is not larger than one batch, so make sure
    # _PAGE_SIZE isn't larger than _BATCH_TARGET_SIZE
    _PAGE_SIZE = 100
    for lang in SUPPORTED_LANGUAGES.__members__:
        more_pages = True
        page_number = 0
        while more_pages:
            # This query should eventually return every document
            paginated_info = ElasticDAL.get_recent_paginated_tickets(
                lang, "", page=page_number, limit=_PAGE_SIZE
            )
            more_pages = paginated_info["deepest_index"] < paginated_info["total_records"]
            document_batch += paginated_info["data"]
            page_number += 1
            if len(document_batch) >= _BATCH_TARGET_SIZE:
                split_beta_batches_and_run_detector(document_batch)
                document_batch = []
    if document_batch:
        split_beta_batches_and_run_detector(document_batch)


def run_spike_worker() -> None:
    """
    Main method for the spike worker thread.
    Determines first if a forceful refresh of all spikes is necessary. If so,
    perform this forceful refresh and exit. If not necessary, perform spike
    detection incrementally.
    """

    s3_client = None
    if _config.get_nested(["s3_document_cache", "endpoint_url"]):
        s3_client = s3.S3Client(_config.get_nested(["s3_document_cache", "endpoint_url"]))
    else:
        s3_client = s3.S3Client()
    s3_bucket_name = _config.get_nested(["s3_document_cache", "bucket_name"])

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

    if is_lock_held and not is_lock_expired:
        print("Lock already held, exiting early")
        return
    # Lock was not held, claim the lock.
    print("Grabbing lock")
    s3_client.upload(s3_bucket_name, _SPIKE_CALCULATOR_LOCK_FILE, "1")

    try:
        # Quick check to see if we have any spikes
        min_max_spike_dates = ElasticDAL.get_min_and_max_spike_dates()
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
            force_recalculate_all_spikes(s3_client, s3_bucket_name)
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

        for inter_date in yield_intermediate_dates(most_recent_spike_date, todays_date):
            split_beta_batches_and_run_for_date(inter_date)
    finally:
        # Release the lock.
        # We use a finaly clause for this in case we ctrl-c or otherwise kill
        # the process out of order.
        print("Releasing lock")
        s3_client.upload(s3_bucket_name, _SPIKE_CALCULATOR_LOCK_FILE, "0")


if __name__ == "__main__":
    run_spike_worker()
