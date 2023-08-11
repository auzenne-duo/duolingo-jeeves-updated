from duolingo_base.config import Config
from duolingo_base.dal import s3

_config = Config.load_config()


def get_s3_client_and_bucket():
    """
    Returns the s3 bucket and s3 client
    """
    if _config.get_nested(["s3_document_cache", "endpoint_url"]):
        s3_client = s3.S3Client(_config.get_nested(["s3_document_cache", "endpoint_url"]))
    else:
        s3_client = s3.S3Client()
    s3_bucket_name = _config.get_nested(["s3_document_cache", "bucket_name"])
    return s3_client, s3_bucket_name


def download_from_jeeves_s3(filename: str) -> bytes:
    """
    Downloads data from jeeves document cache in s3 using given filename
    """
    s3_client, s3_bucket_name = get_s3_client_and_bucket()
    return s3_client.download(s3_bucket_name, filename)


def _upload_to_s3(filename, data, bucket):
    """
    Uploads data to s3 under filename
    """
    s3_client = s3.S3Client()
    s3_client.upload(bucket, filename, data)


def upload_to_public_static(filename, data):
    _upload_to_s3(filename, data, _config.get_nested(["s3_public_static", "bucket_name"]))


def upload_to_internal_static(filename, data):
    _upload_to_s3(filename, data, _config.get_nested(["s3_internal_static", "bucket_name"]))


def upload_to_jeeves_s3(filename, data):
    """
    Uploads data to jeeves document cache in s3 under filename
    """
    _, s3_bucket_name = get_s3_client_and_bucket()
    _upload_to_s3(filename, data, s3_bucket_name)
