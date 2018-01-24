from datetime import datetime
import os
import sys
import time
from tqdm import tqdm

from jeeves import data_directory
from jeeves.dal.support_tickets import ZendeskFileSystemSupportTicketDAL, extract_ticket_timestamp
from jeeves.model.time_series import MOST_RECENT_N_DAYS
from jeeves.util.s3 import S3, S3_ZENDESK_DIR, S3_SEGMENTED_DIR, S3_BUCKET_ID

from export_zendesk import downloadZendesk


_CONTENT_TYPE = 'text/plain; charset=utf-8'
_LOCAL_ZENDESK_DIR = os.path.join(data_directory, 'zendesk')


def deleteExistingTickets():
    """ Deletes local zendesk ticket files. """
    print('Emptying Zendesk directory of existing ticket files', file=sys.stderr)
    for the_file in os.listdir(_LOCAL_ZENDESK_DIR):
        file_path = os.path.join(_LOCAL_ZENDESK_DIR, the_file)
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
        except Exception as e:
            print(e, file=sys.stderr)


def downloadS3Tickets():
    # Grab all zendesk data from S3 and save locally
    print('Downloading S3 Tickets', file=sys.stderr)
    today = datetime.today()
    for remoteFilePath in tqdm(list(S3.yield_filenames(S3_BUCKET_ID, S3_ZENDESK_DIR)),
                               desc='Download Zendesk Tix'):
        remoteFileName = os.path.basename(remoteFilePath)
        timestamp = extract_ticket_timestamp(remoteFileName)
        ticket_date = datetime.fromtimestamp(timestamp)
        if (today - ticket_date).days <= MOST_RECENT_N_DAYS:
            with open(os.path.join(_LOCAL_ZENDESK_DIR, remoteFileName), 'wb') as f:
                f.write(S3.download(S3_BUCKET_ID, os.path.join(S3_ZENDESK_DIR, remoteFileName)))


def downloadNewTicketsAndUploadToS3():
    """ Downloads recent tickets from Zendesk and uploads them to S3. """
    # Get most recent Zendesk timestamp and the current timestamp
    try:
        latestTimeStamp = max(extract_ticket_timestamp(filename)
                              for filename in S3.yield_filenames(S3_BUCKET_ID, S3_ZENDESK_DIR))
    except ValueError:
        # if nothing is in S3, start on December 1st
        latestTimeStamp = 1480550400  # 2016-12-01
    currentTimestamp = int(time.time())

    print('Downloading new tickets since {}'.format(datetime.fromtimestamp(latestTimeStamp)
                                                    .strftime('%Y-%m-%d %H:%M:%S')))

    # Upload all new Zendesk ticket files to S3
    newFiles = downloadZendesk(latestTimeStamp, currentTimestamp)

    for file_name in tqdm(newFiles, desc='Upload Zendesk Tix'):
        with open(os.path.join(_LOCAL_ZENDESK_DIR, file_name), 'r') as f:
            data = f.read()
            S3.upload(S3_BUCKET_ID, os.path.join(S3_ZENDESK_DIR, file_name), data, _CONTENT_TYPE)


def recreateAndUploadSegmentedFiles():
    # Recreate Segmented Support Ticket Files
    print('Creating Segmented Support Tickets', file=sys.stderr)
    segmentedFilePaths = ZendeskFileSystemSupportTicketDAL().segment_labeled_support_tickets()

    print('Uploading Segmented Support Tickets to S3', file=sys.stderr)
    # And upload them to S3
    for segFilePath in tqdm(segmentedFilePaths, desc='Upload Segmented Tix'):
        with open(segFilePath, 'r') as f:
            data = f.read()
            bName = os.path.basename(segFilePath)
            S3.upload(S3_BUCKET_ID, os.path.join(S3_SEGMENTED_DIR, bName), data, _CONTENT_TYPE)

    print('Successfully updated S3 data!!', file=sys.stderr)


if __name__ == '__main__':
    if not os.getenv('ZENDESK_USER') or not os.getenv('ZENDESK_PASSWORD'):
        print('Please set the environment variables ZENDESK_USER and ZENDESK_PASSWORD.')
        sys.exit()

    deleteExistingTickets()
    downloadS3Tickets()
    downloadNewTicketsAndUploadToS3()
    recreateAndUploadSegmentedFiles()
