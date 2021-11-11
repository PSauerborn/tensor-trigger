"""Module containing utility functions"""

import logging
import io
import base64
import re
from typing import Union
from collections import namedtuple

from fastapi import Request, status
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse

LOGGER = logging.getLogger(__name__)
DATA_REGEX = r'^data:(.*);base64,(.*)'


def json_response_with_message(code: int, message: str) -> JSONResponse:
    """Utility function used to generate boiler
    plat JSONResponse with message and code
    Args:
        code (int): HTTP Code
        message (str): message
    Returns:
        JSONResponse: formatted JSONResponse
            instance
    """

    content = {'http_code': code, 'message': message}
    return JSONResponse(status_code=code, content=content)


def get_user(raise_if_none: bool = True) -> Union[str, None]:
    """Function used to extract user ID from
    headers

    Args:
        request (Request): FastAPI request instance

    Returns:
        Union[str, None]: string containing user ID
            if present else None
    """

    def wrapper(request: Request):
        uid = request.headers.get('X-Authenticated-Userid', None)
        if uid is None and raise_if_none:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Forbidden')
        return uid
    return wrapper


class InvalidBase64FileException(Exception):
    """Exception raised when an invalid base64
    file is received for upload"""

Base64FileMetadata = namedtuple('Base64FileMetadata', ['file_size', 'mime_type'])

def parse_base64_file(contents: str) -> Base64FileMetadata:
    """Function used to parse contents of base64
    encoded file
    Args:
        contents (str): [description]
    Returns:
        Base64FileMetadata: [description]
    """

    try:
        mime_type, contents = re.findall(DATA_REGEX, contents)[0]
        file_size = get_file_size(contents)
        # generate file metadata and convert data to
        # bytesIO instance
        meta = Base64FileMetadata(file_size=file_size, mime_type=mime_type)
        return meta, base64toBytesIO(contents)

    except ValueError:
        LOGGER.exception('unable to parse file: invalid file format')
        raise InvalidBase64FileException


def get_file_size(contents: str) -> int:
    """Function used to determine file size
    for a given file that has been base64
    encoded
    Args:
        contents (str): base64 encoded string
    Returns:
        int: size of file
    """

    return (len(contents) * 3) / 4 - contents.count('=', -2)


def base64toBytesIO(contents: str) -> io.BytesIO:
    """Function used to convert base64 encoded
    string into a BytesIO instance
    Args:
        contents (str): base64 encoded string
            to convert
    Returns:
        io.BytesIO: BytesIO instance containing file data
    """

    try:
        # decode file from base64 and convert to BytesIO instance
        file_data = base64.b64decode(contents)
        return io.BytesIO(file_data)

    except Exception:
        LOGGER.exception('unable to parse file contents')
        raise InvalidBase64FileException


def generate_base64_file(contents: io.BytesIO, meta: Base64FileMetadata) -> str:
    """Function used to convert file contents
    into base64 encoded string
    Args:
        contents (io.BytesIO): [description]
        meta (Base64FileMetadata): [description]
    Returns:
        str: [description]
    """

    # generate string data and return base64 endoed
    bytes_data = contents.getbuffer()
    b64_encoded = base64.b64encode(bytes_data).decode()
    return 'data:{};base64,{}'.format(meta.mime_type, b64_encoded)