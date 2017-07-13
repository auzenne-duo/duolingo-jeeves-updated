import os
import re
import sys
import time

from jeeves import data_directory
from jeeves.dal.support_tickets import ZendeskFileSystemSupportTicketDAL
from jeeves.util.s3 import S3, S3_ZENDESK_DIR, S3_SEGMENTED_DIR, S3_BUCKET_ID

from export_zendesk import downloadZendesk

_CONTENT_TYPE = 'text/plain; charset=utf-8'
_LOCAL_ZENDESK_DIR = os.path.join(data_directory, 'zendesk')

print('Emptying Zendesk directory of existing ticket files', file=sys.stderr)
for the_file in os.listdir(_LOCAL_ZENDESK_DIR):
    file_path = os.path.join(_LOCAL_ZENDESK_DIR, the_file)
    try:
        if os.path.isfile(file_path):
            os.remove(file_path)
    except Exception as e:
        print(e, file=sys.stderr)

# Grab all zendesk data from S3 and save locally
print('Downloading S3 Tickets', file=sys.stderr)
for remoteFilePath in S3.yield_filenames(S3_BUCKET_ID, S3_ZENDESK_DIR):
    remoteFileName = os.path.basename(remoteFilePath)
    with open(os.path.join(_LOCAL_ZENDESK_DIR, remoteFileName), 'wb') as zFile:
        zFile.write(
            S3.download(
                S3_BUCKET_ID,
                os.path.join(
                    S3_ZENDESK_DIR,
                    remoteFileName
                )
            )
        )

# Get most recent Zendesk timestamp and the current timestamp
_TICKET_FILE_REGEX = re.compile(r'^tickets_(\d+)\.json$')
try:
    latestTimeStamp = max(
        int(m.group(1))
        for m in map(
            _TICKET_FILE_REGEX.match,
            S3.yield_filenames(S3_BUCKET_ID, S3_ZENDESK_DIR)
        )
        if m is not None
    )
except ValueError:
    # if nothing is in S3, start on December 1st
    latestTimeStamp = 1480550400  # 2016-12-01
currentTimestamp = int(time.time())

# Upload all new Zendesk ticket files to S3
newFiles = downloadZendesk(latestTimeStamp, currentTimestamp)

for fName in newFiles:
    with open(os.path.join(_LOCAL_ZENDESK_DIR, fName), 'r') as f:
        data = f.read()
        S3.upload(S3_BUCKET_ID, os.path.join(S3_ZENDESK_DIR, fName), data, _CONTENT_TYPE)

# Recreate Segmented Support Ticket Files
print('Creating Segmented Support Tickets', file=sys.stderr)
segmentedFilePaths = ZendeskFileSystemSupportTicketDAL().segment_labeled_support_tickets()

print('Uploading Segmented Support Tickets to S3', file=sys.stderr)
# And upload them to S3
for segFilePath in segmentedFilePaths:
    with open(segFilePath, 'r') as f:
        data = f.read()
        bName = os.path.basename(segFilePath)
        S3.upload(S3_BUCKET_ID, os.path.join(S3_SEGMENTED_DIR, bName), data, _CONTENT_TYPE)

print('Successfully updated S3 data!!', file=sys.stderr)
