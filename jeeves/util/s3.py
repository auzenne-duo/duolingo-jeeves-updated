"""
Utility functions to access files on Amazon S3.

Based on https://github.com/duolingo/duolingo-tts/blob/master/tts/util/s3.py
"""
import boto3
from botocore.client import ClientError
import os
import time

from jeeves.exception.util import S3UploadException

S3_ZENDESK_DIR = os.path.join('data', 'zendesk')
S3_SEGMENTED_DIR = os.path.join('data', 'segmented')
S3_SPIKE_DIR = os.path.join('data', 'spike')
S3_BUCKET_ID = 'duolingo-jeeves'

class S3Manager(object):
    """ Manages S3 connections. """

    @staticmethod
    def _get_bucket(bucket_id):
        """
        Returns:
            An S3 bucket.
        """
        s3 = boto3.resource('s3')
        return s3.Bucket(bucket_id)

    def upload(self, bucket_id, path, data, content_type, num_retries=1, wait_time=1):
        """
        Parameters:
            bucket_id (str): S3 bucket ID.
            path (str): Path to which the file will be uploaded.
            data (bytes): Bytes for the file.
            content_type (str): Content type of the data.
            num_retries (int, optional): Number of retries before giving up.
            wait_time (int, optional): Number of seconds between each retry.
        """
        s3_bucket = self._get_bucket(bucket_id)
        s3_key = s3_bucket.Object(path)

        # Uploads with retry
        def _upload(s3_key):
            s3_key.put(Metadata={'Content-Type': content_type})
            s3_key.put(Body=data)
            s3_key.Acl().put(ACL='public-read')

        success = False
        s3_error = None
        for _ in range(num_retries + 1):
            try:
                _upload(s3_key)
                success = True
                break
            except ClientError as response_error:
                s3_error = response_error
                time.sleep(wait_time)

        if not success:
            raise S3UploadException(s3_error.response['Error']['Message'])

    def download(self, bucket_id, path):
        """
        Parameters:
            bucket_id (str): S3 bucket ID.
            path (str): Path from which the file will be downloaded.

        Returns:
            Bytes or a string containing the file content.
        """
        s3_bucket = self._get_bucket(bucket_id)
        s3_key = s3_bucket.Object(path)
        return s3_key.get()["Body"].read().decode('utf-8')

    def yield_filenames(self, bucket_id, path_prefix=''):
        """
        Parameters:
            bucket_id (str): S3 bucket ID.
            path_prefix (str, optional): Prefix of path in which to search for files.

        Yields:
            The filename (str) for every file in the bucket that matches the given prefix.
        """
        client = boto3.client('s3')
        paginator = client.get_paginator('list_objects')
        s3_bucket = self._get_bucket(bucket_id)
        page_iterator = paginator.paginate(Bucket=s3_bucket.name, Prefix='%s/' % path_prefix)
        for page in page_iterator:
            keys = [content['Key'] for content in page['Contents']]
            for s3_filename in [key.split('/')[-1] for key in keys if not key.endswith('/')]:
                yield s3_filename


S3 = S3Manager()
