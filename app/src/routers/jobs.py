"""Module containing API router for tensor
trigger functionality"""

import logging
import json
from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.encoders import jsonable_encoder as je
from fastapi.responses import JSONResponse

from src.utils import json_response_with_message, get_user, \
    generate_base64_file, Base64FileMetadata
from src.persistence.postgres import get_user_jobs, get_user_job, \
    get_user_model
from src.persistence.s3 import retrieve_s3_file
from src.config import PG_CREDENTIALS
from src.logic.tensor import _format_output_vector

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
    jobs = [j._asdict() for j in get_user_jobs(PG_CREDENTIALS, uid)]
    content = {'http_code': status.HTTP_200_OK, 'jobs': jobs}
    return JSONResponse(status_code=status.HTTP_200_OK, content=je(content))


@ROUTER.get('/{job_id}/metadata')
async def get_model_meta_handler(job_id: UUID, uid: str = Depends(get_user())) -> JSONResponse:
    """API handler used to retrieve models
    for a given user

    Returns:
        JSONResponse: [description]
    """

    LOGGER.debug('retrieving models for user %s', uid)
    # get all models from postgres database and convert to dict
    job = get_user_job(PG_CREDENTIALS, uid, job_id)
    if job is None:
        LOGGER.error('unable to find job %s for user %s', job_id, uid)
        return json_response_with_message(status.HTTP_404_NOT_FOUND, 'Cannot find specified job')

    content = {'http_code': status.HTTP_200_OK, 'job': job._asdict()}
    return JSONResponse(status_code=status.HTTP_200_OK, content=je(content))


@ROUTER.get('/{job_id}/content')
async def get_model_content_handler(job_id: UUID, uid: str = Depends(get_user())) -> JSONResponse:
    """API handler used to retrieve models
    for a given user

    Returns:
        JSONResponse: [description]
    """

    LOGGER.debug('retrieving models for user %s', uid)
    # get all models from postgres database and convert to dict
    job = get_user_job(PG_CREDENTIALS, uid, job_id)
    if job is None:
        LOGGER.error('unable to find job %s for user %s', job_id, uid)
        return json_response_with_message(status.HTTP_404_NOT_FOUND, 'Cannot find specified job')

    s3_data = retrieve_s3_file('/tensor-trigger/input-data' + str(job.job_id))
    # generate metadata for file (including mime type) and convert to
    # base64 encoded format
    meta = Base64FileMetadata(file_size=0, mime_type='text/plain')
    content = {'http_code': status.HTTP_200_OK,
               'job': generate_base64_file(s3_data, meta)}
    return JSONResponse(status_code=status.HTTP_200_OK, content=je(content))


@ROUTER.get('/{job_id}/results')
async def get_job_results_handler(job_id: UUID, uid: str = Depends(get_user())) -> JSONResponse:
    """API handler used to retrieve models
    for a given user

    Returns:
        JSONResponse: [description]
    """

    LOGGER.debug('retrieving models for user %s', uid)
    # get all models from postgres database and convert to dict
    job = get_user_job(PG_CREDENTIALS, uid, job_id)
    if job is None:
        LOGGER.error('unable to find job %s for user %s', job_id, uid)
        return json_response_with_message(status.HTTP_404_NOT_FOUND, 'Cannot find specified job')

    if job.job_state != 2:
        LOGGER.error('unable to retrieve job results for %s: invalid job state %s', job_id, job.job_state)
        return json_response_with_message(status.HTTP_400_BAD_REQUEST, 'Invalid job state')

    meta = get_user_model(PG_CREDENTIALS, uid, job.model_id)
    schema = meta.model_schema

    s3_data = retrieve_s3_file('/tensor-trigger/output-data' + str(job.job_id))
    results = json.loads(s3_data.getvalue().decode())
    # generate metadata for file (including mime type) and convert to
    # base64 encoded format
    meta = Base64FileMetadata(file_size=0, mime_type='text/plain')
    content = {'http_code': status.HTTP_200_OK,
               'results': _format_output_vector(results.get('output', []), schema.get('output_schema'))}
    return JSONResponse(status_code=status.HTTP_200_OK, content=je(content))