import logging
import json
from contextlib import contextmanager
from enum import Enum
from typing import NamedTuple, List, Union
from uuid import UUID, uuid4

import psycopg2
from psycopg2.extras import register_uuid, DictCursor, NamedTupleCursor
from pydantic import BaseModel, SecretStr


LOGGER = logging.getLogger(__name__)


class CursorFactory(Enum):
    DICT_CURSOR = DictCursor
    NAMED_TUPLE_CURSOR = NamedTupleCursor


class PostgresCredentials(BaseModel):
    """Data class containing fields used to
    store postgres connection settings"""

    PG_HOST: str
    PG_DATABASE: str
    PG_USER: str
    PG_PASSWORD: SecretStr
    PG_PORT: int = 5432


@contextmanager
def get_cursor(credentials: PostgresCredentials, cursor_factory: CursorFactory = CursorFactory.NAMED_TUPLE_CURSOR):
    """Returns a cursor as context manager.

    Returns a cursor as a context manager using the credentials
    matching the `connection_name` from the PostgresCredentialsManager.
    Args:
        connection_name (str): The database name in the PostgresCredentialManager.
        cursor_factory (CursorFactory): The cursor factory to user.

    Returns:
        cursor (psycopg2.cursor): A cursor to be used as a context manager.
    """

    with get_connection(credentials) as connection:
        cursor = connection.cursor(cursor_factory=cursor_factory.value)
        try:
            yield cursor
            connection.commit()
        finally:
            cursor.close()


@contextmanager
def get_connection(credentials: PostgresCredentials):
    connection = psycopg2.connect(
        dbname=credentials.PG_DATABASE,
        user=credentials.PG_USER,
        host=credentials.PG_HOST,
        password=credentials.PG_PASSWORD.get_secret_value(),
        port=credentials.PG_PORT
    )
    register_uuid(conn_or_curs=connection)

    try:
        yield connection
    finally:
        connection.close()

