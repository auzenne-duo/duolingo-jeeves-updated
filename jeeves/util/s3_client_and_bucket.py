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
