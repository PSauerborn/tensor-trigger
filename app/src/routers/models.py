"""Module containing API router for tensor
trigger functionality"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.encoders import jsonable_encoder as je
from fastapi.responses import JSONResponse

from src.utils import json_response_with_message, get_user, \
    generate_base64_file, Base64FileMetadata, parse_base64_file
from src.persistence.postgres import get_user_model, get_user_models, \
    insert_user_model, delete_user_model
from src.persistence.s3 import upload_s3_file, retrieve_s3_file, \
    delete_s3_file
from src.config import PG_CREDENTIALS
from src.models.models import ModelUploadRequest
from src.logic.tensor import validate_upload_content


LOGGER = logging.getLogger(__name__)
ROUTER = APIRouter()

@ROUTER.get('')
async def get_models_handler(uid: str = Depends(get_user())) -> JSONResponse:
    """API handler used to retrieve models
    for a given user

    Returns:
        JSONResponse: [description]
    """

    LOGGER.debug('retrieving models for user %s', uid)
    # get all models from postgres database and convert to dict
    models = [m._asdict() for m in get_user_models(PG_CREDENTIALS, uid)]
    content = {'http_code': status.HTTP_200_OK,
               'models': models}
    return JSONResponse(status_code=status.HTTP_200_OK, content=je(content))


@ROUTER.get('/{model_id}/content')
async def get_model_handler(model_id: UUID, uid: str = Depends(get_user())) -> JSONResponse:
    """API handler used to retrieve model by
    model ID for a given user

    Returns:
        JSONResponse: [description]
    """

    LOGGER.debug('retrieving model %s for user %s', model_id, uid)
    model_meta = get_user_model(PG_CREDENTIALS, uid, model_id)
    if model_meta is None:
        return json_response_with_message(status.HTTP_404_NOT_FOUND, 'Cannot find specified model')

    s3_data = retrieve_s3_file('/tensor-trigger/' + str(model_id))
    # generate metadata for file (including mime type) and convert to
    # base64 encoded format
    meta = Base64FileMetadata(file_size=0, mime_type='application/octet-stream')
    content = {'http_code': status.HTTP_200_OK,
               'model': generate_base64_file(s3_data, meta)}
    return JSONResponse(status_code=status.HTTP_200_OK, content=je(content))


@ROUTER.get('/{model_id}/metadata')
async def get_model_meta_handler(model_id: UUID, uid: str = Depends(get_user())) -> JSONResponse:
    """API handler used to retrieve model by
    model ID for a given user

    Returns:
        JSONResponse: [description]
    """

    LOGGER.debug('retrieving model %s for user %s', model_id, uid)
    model_meta = get_user_model(PG_CREDENTIALS, uid, model_id)
    if model_meta is None:
        return json_response_with_message(status.HTTP_404_NOT_FOUND, 'Cannot find specified model')

    content = {'http_code': status.HTTP_200_OK,
               'model': model_meta._asdict()}
    return JSONResponse(status_code=status.HTTP_200_OK, content=je(content))


@ROUTER.post('/new')
async def new_model_handler(r: ModelUploadRequest, uid: str = Depends(get_user())) -> JSONResponse:
    """API handler used to retrieve model by
    model ID for a given user

    Returns:
        JSONResponse: [description]
    """

    LOGGER.debug('received request to upload new model for user %s', uid)
    # insert into postgres database and retrieve model ID
    try:
        meta, bytes_data = parse_base64_file(r.model_content)
        # try to parse uploaded content to tensorflow model
        expected_shapes = validate_upload_content(bytes_data, r.model_schema)
        bytes_data.seek(0)
    except Exception:
        LOGGER.exception('unable to parse file')
        return json_response_with_message(status.HTTP_400_BAD_REQUEST, 'Invalid model data')

    model_id = insert_user_model(PG_CREDENTIALS,
                                 uid,
                                 r.model_name,
                                 r.model_description,
                                 r.model_schema,
                                 meta.file_size,
                                 expected_shapes.input_shape,
                                 expected_shapes.output_shape)
    # upload data to s3 bucket
    upload_s3_file(bytes_data, '/tensor-trigger/' + str(model_id))
    return json_response_with_message(status.HTTP_201_CREATED, 'Successfully created model')


@ROUTER.delete('/{model_id}')
async def delete_model_handler(model_id: UUID, uid: str = Depends(get_user())) -> JSONResponse:
    """API handler used to delete model

    Args:
        model_id (UUID): [description]
        uid (str, optional): [description]. Defaults to Depends(get_user()).

    Returns:
        JSONResponse: [description]
    """

    LOGGER.debug('deleting model %s for user %s', model_id, uid)
    model_meta = get_user_model(PG_CREDENTIALS, uid, model_id)
    if model_meta is None:
        return json_response_with_message(status.HTTP_404_NOT_FOUND, 'Cannot find specified model')

    # delete model from S3 bucket and from postgres database
    delete_s3_file('/tensor-trigger/' + str(model_id))
    delete_user_model(PG_CREDENTIALS, uid, model_id)

    content = {'http_code': status.HTTP_200_OK,
               'message': 'Successfully deleted model'}
    return JSONResponse(status_code=status.HTTP_200_OK, content=content)
