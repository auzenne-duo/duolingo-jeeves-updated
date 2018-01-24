from datetime import datetime
import os
import sys
from tqdm import tqdm

from jeeves import data_directory
from jeeves.dal.support_tickets import ZendeskFileSystemSupportTicketDAL, extract_ticket_timestamp
from jeeves.lib.file_io import read_from_file, write_to_file
from jeeves.lib.zendesk_ticket_downloader import download_tickets
from jeeves.model.time_series import MOST_RECENT_N_DAYS
from jeeves.util.s3 import S3, S3_ZENDESK_DIR, S3_SEGMENTED_DIR, S3_BUCKET_ID


_CONTENT_TYPE = 'text/plain; charset=utf-8'
_LOCAL_ZENDESK_DIR = os.path.join(data_directory, 'zendesk')


def delete_local_tickets():
    """ Deletes local zendesk ticket files. """
    print('Emptying Zendesk directory of existing ticket files', file=sys.stderr)
    for the_file in os.listdir(_LOCAL_ZENDESK_DIR):
        file_path = os.path.join(_LOCAL_ZENDESK_DIR, the_file)
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
        except Exception as e:
            print(e, file=sys.stderr)


def get_tickets_from_s3():
    # Grab all zendesk data from S3 and save locally
    print('Downloading S3 Tickets', file=sys.stderr)
    remote_files = list(S3.yield_filenames(S3_BUCKET_ID, S3_ZENDESK_DIR))
    print('Number of remote files:', len(remote_files))
    today = datetime.today()
    for remote_file_path in tqdm(remote_files, desc='Download Zendesk Tix'):
        file_name = os.path.basename(remote_file_path)
        timestamp = extract_ticket_timestamp(file_name)
        ticket_date = datetime.fromtimestamp(timestamp)
        if (today - ticket_date).days <= MOST_RECENT_N_DAYS:
            ticket_json = S3.download(S3_BUCKET_ID, os.path.join(S3_ZENDESK_DIR, file_name))
            write_to_file(ticket_json + '.gz', file_name, dir_path=_LOCAL_ZENDESK_DIR)


def get_tickets_from_zendesk():
    """ Downloads recent tickets from Zendesk and uploads them to S3. """
    # Get most recent Zendesk timestamp and the current timestamp
    try:
        latest_timestamp = max(extract_ticket_timestamp(filename)
                              for filename in S3.yield_filenames(S3_BUCKET_ID, S3_ZENDESK_DIR))
    except ValueError:
        # if nothing is in S3, start on December 1st
        latest_timestamp = 1480550400  # 2016-12-01

    print('Downloading new tickets since {}'.format(datetime.fromtimestamp(latest_timestamp)
                                                    .strftime('%Y-%m-%d %H:%M:%S')))

    # Download all new Zendesk ticket files and upload them to S3
    new_files = download_tickets(latest_timestamp)

    for file_name in tqdm(new_files, desc='Upload Zendesk Tix'):
        data = read_from_file(file_name + '.gz', dir_path=_LOCAL_ZENDESK_DIR)
        S3.upload(S3_BUCKET_ID, os.path.join(S3_ZENDESK_DIR, file_name), data, _CONTENT_TYPE)


def crete_segmented_tickets():
    # Recreate Segmented Support Ticket Files
    segmented_file_paths = ZendeskFileSystemSupportTicketDAL().segment_labeled_support_tickets()
    print('Creating Segmented Support Tickets', file=sys.stderr)

    print('Uploading Segmented Support Tickets to S3', file=sys.stderr)
    # And upload them to S3
    for file_path in tqdm(segmented_file_paths, desc='Upload Segmented Tix'):
        file_name = os.path.basename(file_path)
        data = read_from_file(file_name + '.gz', dir_path=data_directory)
        S3.upload(S3_BUCKET_ID, os.path.join(S3_SEGMENTED_DIR, file_name), data, _CONTENT_TYPE)

    print('Successfully updated S3 data!!', file=sys.stderr)


if __name__ == '__main__':
    if not os.getenv('ZENDESK_USER') or not os.getenv('ZENDESK_PASSWORD'):
        print('Please set the environment variables ZENDESK_USER and ZENDESK_PASSWORD.')
        sys.exit()

    # 1. Delete tickets in local files
    delete_local_tickets()
    # 2. Download recent tickets from S3, write them to local files
    get_tickets_from_s3()
    # 3. Download recent tickets from Zendesk, write them to local files and S3
    get_tickets_from_zendesk()
    # 4. Create segmented tickets, write them to local files and then S3
    crete_segmented_tickets()
