from jeeves.exception import JeevesException

class S3UploadException(JeevesException):
    """
    Error to be thrown when we cannot upload to S3.
    """
    pass
