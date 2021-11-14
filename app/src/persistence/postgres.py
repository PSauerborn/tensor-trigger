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


def get_user_models(creds: PostgresCredentials, uid: str) -> List[NamedTuple]:
    """DB function used to retrieve
    models for a given user

    Args:
        uid (str): [

    Returns:
        List[NamedTuple]: [description]
    """

    with get_cursor(creds) as db:
        db.execute('SELECT model_id,model_name,model_description,model_schema,size,created,input_shape,output_shape FROM models '
                   'WHERE username=%s', (uid,))
        results = db.fetchall()
    return list(results) if results else []


def get_user_model(creds: PostgresCredentials, uid: str, model_id: UUID) -> Union[NamedTuple, None]:
    """DB function used to retrieve user models
    by username and model ID

    Args:
        creds (PostgresCredentials): [description]
        uid (str): [description]
        model_id (UUID): [description]

    Returns:
        Union[NamedTuple, None]: [description]
    """

    with get_cursor(creds) as db:
        db.execute('SELECT model_id,model_name,model_description,model_schema,size,created,input_shape,output_shape FROM models '
                   'WHERE username=%s AND model_id=%s', (uid, model_id))
        result = db.fetchone()
    return result if result else None

def insert_user_model(creds: PostgresCredentials,
                      uid: str,
                      name: str,
                      description: str,
                      schema: dict,
                      size: int,
                      input_shape: int,
                      output_shape: int) -> UUID:
    """DB function used to insert new model into
    database

    Args:
        creds (PostgresCredentials): [description]
        uid (str): [description]
        name (str): [description]
        description (str): [description]

    Returns:
        UUID: [description]
    """

    def format_schema_item(row: dict) -> dict:
        row.var_type = row.var_type.upper()
        return row.dict()

    model_id = uuid4()
    # cast all data types to upper case
    schema = {k: format_schema_item(v) for k, v in schema.items()}
    with get_cursor(creds) as db:
        db.execute('INSERT INTO models(model_id,username,model_name,model_description,model_schema,size,input_shape,output_shape) '
                   'VALUES(%s,%s,%s,%s,%s,%s,%s,%s)', (model_id, uid, name, description, json.dumps(schema), size, input_shape, output_shape))
    return model_id


def insert_async_job(creds: PostgresCredentials, model_id: UUID, upload_size: int) -> UUID:
    """DB function used to insert new async
    job into database

    Args:
        creds (PostgresCredentials): [description]
        model_id (UUID): [description]
        upload_size (int): [description]

    Returns:
        UUID: [description]
    """

    job_id = uuid4()
    with get_cursor(creds) as db:
        db.execute('INSERT INTO async_jobs(job_id,model_id,upload_size) VALUES(%s,%s,%s)',
                   (job_id, model_id, upload_size))
    return job_id


def get_user_jobs(creds: PostgresCredentials, uid: str) -> List[NamedTuple]:
    """DB function used to retrieve all jobs for a given user

    Args:
        creds (PostgresCredentials): [description]

    Returns:
        List[NamedTuple]: [description]
    """

    with get_cursor(creds) as db:
        db.execute('SELECT j.job_id,j.model_id,j.upload_size,j.created,j.last_updated,j.job_state '
                   'FROM async_jobs AS j '
                   'INNER JOIN models ON models.model_id = j.model_id '
                   'WHERE models.username = %s', (uid,))
        results = db.fetchall()
    return results if results else []


def get_user_job(creds: PostgresCredentials, uid: str, job_id: UUID) -> List[NamedTuple]:
    """DB function used to retrieve all jobs for a given user

    Args:
        creds (PostgresCredentials): [description]

    Returns:
        List[NamedTuple]: [description]
    """

    with get_cursor(creds) as db:
        db.execute('SELECT j.job_id,j.model_id,j.upload_size,j.created,j.last_updated,j.job_state '
                   'FROM async_jobs AS j '
                   'INNER JOIN models ON models.model_id = j.model_id '
                   'WHERE models.username = %s AND j.job_id = %s', (uid, job_id))
        result = db.fetchone()
    return result if result else None


def delete_user_model(creds: PostgresCredentials, uid: str, model_id: UUID):
    """DB function used to delete user model
    from database

    Args:
        creds (PostgresCredentials): [description]
        uid (str): [description]
        model_id (UUID): [description]

    Returns:
        [type]: [description]
    """

    with get_cursor(creds) as db:
        db.execute('DELETE FROM models WHERE model_id = %s AND username = %s', (model_id, uid))
