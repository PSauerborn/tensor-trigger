"""Module containing functions used to interact with S3
layer"""

import logging
import io

import boto3

from src.config import S3_REGION_NAME, S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY, \
    S3_BUCKET_NAME

LOGGER = logging.getLogger(__name__)

# generate new AWS client with credentials
# and region to interface with S3
CLIENT = boto3.client(
    's3',
    aws_access_key_id=S3_ACCESS_KEY_ID,
    aws_secret_access_key=S3_SECRET_ACCESS_KEY,
    region_name=S3_REGION_NAME
)


def retrieve_s3_file(path: str) -> io.BytesIO:
    """Function used to retrieve a file
    from an S3 bucket

    Returns:
        io.BytesIO: [description]
    """

    # generate new instance of bytesIO and download
    # contents of s3 bucket into data stream
    content = io.BytesIO()
    CLIENT.download_fileobj(S3_BUCKET_NAME, path, content)
    return content


def upload_s3_file(content: io.BytesIO, path: str):
    """Function used to upload file to
    S3 bucket

    Returns:
        io.BytesIO: [description]
    """

    CLIENT.upload_fileobj(content, S3_BUCKET_NAME, path)
