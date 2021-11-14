"""Module containing API router for tensor
trigger functionality"""

import logging
import json

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder as je

from src.utils import get_user,json_response_with_message, parse_base64_file
from src.persistence.postgres import get_user_model, insert_async_job
from src.persistence.s3 import retrieve_s3_file, upload_s3_file
from src.config import PG_CREDENTIALS, MESSAGE_BROKER_URL, JOB_EXCHANGE_NAME, \
    JOB_EXCHANGE_TYPE, JOB_ROUTING_KEY
from src.logic.tensor import validate_data_point, run_model, \
    run_model_batched, validate_csv_file
from src.models.tensor import ProcessRequest, BatchProcessRequest, \
    AsyncBatchProcessRequest, TrainModelRequest
from src.services.rabbitmq import write_to_exchange


LOGGER = logging.getLogger(__name__)
ROUTER = APIRouter()


@ROUTER.post('/run')
async def run_model_handler(r: ProcessRequest, uid: str = Depends(get_user())) -> JSONResponse:
    """API handler used to run model
    for a given datapoint

    Args:
        model_id (UUID): UUID of model to run
        uid (str, optional): [description]. Defaults to Depends(get_user()).

    Returns:
        JSONResponse: [description]
    """

    LOGGER.debug('received request to run model for user %s', uid)
    # get model metadata from postgres server. return
    # 404 error code if model cannot be found
    model_meta = get_user_model(PG_CREDENTIALS, uid, r.model_id)
    if model_meta is None:
        LOGGER.error('unable to retrieve model %s for user %s', r.model_id, uid)
        return json_response_with_message(status.HTTP_404_NOT_FOUND, 'Cannot find specified model')

    # validate provided input vector against
    # the schema registered against the model
    if not validate_data_point(r.input_vector, model_meta.model_schema):
        LOGGER.error('unable to validate data point %s against schema %s', r.input_vector, model_meta.model_schema)
        return json_response_with_message(status.HTTP_400_BAD_REQUEST, 'Invalid input vector')

    # retrieve hd5 file from s3 storage and run tensorflow model
    s3_data = retrieve_s3_file('/tensor-trigger/' + str(r.model_id))
    results = run_model(s3_data, r.input_vector, model_meta.model_schema)
    if results is None:
        LOGGER.error('unable to run model %s', r.model_id)
        return json_response_with_message(status.HTTP_500_INTERNAL_SERVER_ERROR, 'Internal server error')

    content = {'http_code': status.HTTP_200_OK, 'output': results}
    return JSONResponse(status_code=status.HTTP_200_OK, content=je(content))


@ROUTER.post('/run/batch')
async def batch_model_handler(r: BatchProcessRequest, uid: str = Depends(get_user())) -> JSONResponse:
    """API handler used to handle batch processing
    of model data

    Args:
        r (BatchProcessRequest): [description]
        uid (str, optional): [description]. Defaults to Depends(get_user()).

    Returns:
        JSONResponse: [description]
    """

    LOGGER.debug('received request to batch process data for user %s', uid)
    # get model metadata from postgres server. return
    # 404 error code if model cannot be found
    model_meta = get_user_model(PG_CREDENTIALS, uid, r.model_id)
    if model_meta is None:
        LOGGER.error('unable to retrieve model %s for user %s', r.model_id, uid)
        return json_response_with_message(status.HTTP_404_NOT_FOUND, 'Cannot find specified model')

    # validate provided input vectors against
    # the schema registered against the model
    invalid_points = any(not validate_data_point(x, model_meta.model_schema) for x in r.input_vectors)
    if invalid_points:
        LOGGER.error('unable to validate data point(s) against schema %s', model_meta.model_schema)
        return json_response_with_message(status.HTTP_400_BAD_REQUEST, 'Invalid input vector(s)')

    # retrieve hd5 file from s3 storage and run tensorflow model
    s3_data = retrieve_s3_file('/tensor-trigger/' + str(r.model_id))
    results = run_model_batched(s3_data, r.input_vectors, model_meta.model_schema)
    if results is None:
        LOGGER.error('unable to run model %s', r.model_id)
        return json_response_with_message(status.HTTP_500_INTERNAL_SERVER_ERROR, 'Internal server error')

    content = {'http_code': status.HTTP_200_OK, 'output': results}
    return JSONResponse(status_code=status.HTTP_200_OK, content=je(content))


@ROUTER.post('/run/async')
async def async_batch_model_handler(r: AsyncBatchProcessRequest, uid: str = Depends(get_user())) -> JSONResponse:
    """API handler used to handle batch processing
    of model data

    Args:
        r (BatchProcessRequest): [description]
        uid (str, optional): [description]. Defaults to Depends(get_user()).

    Returns:
        JSONResponse: [description]
    """

    LOGGER.debug('received request to batch process data async for user %s', uid)
    # get model metadata from postgres server. return
    # 404 error code if model cannot be found
    model_meta = get_user_model(PG_CREDENTIALS, uid, r.model_id)
    if model_meta is None:
        LOGGER.error('unable to retrieve model %s for user %s', r.model_id, uid)
        return json_response_with_message(status.HTTP_404_NOT_FOUND, 'Cannot find specified model')

    try:
        meta, bytes_data = parse_base64_file(r.input_data)
        if not validate_csv_file(bytes_data, model_meta.model_schema):
            LOGGER.error('CSV validation failed')
            raise ValueError
        bytes_data.seek(0)
    except Exception:
        LOGGER.exception('unable to validate file data')
        return json_response_with_message(status.HTTP_400_BAD_REQUEST, 'Invalid input data')

    # insert job into database and upload input data to s3
    job_id = insert_async_job(PG_CREDENTIALS, r.model_id, meta.file_size)
    upload_s3_file(bytes_data, '/tensor-trigger/input-data' + str(job_id))
    content = {'http_code': status.HTTP_201_CREATED,
               'message': 'Successfully queued job',
               'job_id': job_id}

    # send event to RabbitMQ broker to trigger worker
    event = {'job_id': str(job_id),
             'event_type': 'model_run',
             'event': {'model_id': str(r.model_id), 'user': uid}}
    write_to_exchange(MESSAGE_BROKER_URL,
                      JOB_EXCHANGE_NAME,
                      json.dumps(event),
                      JOB_EXCHANGE_TYPE,
                      JOB_ROUTING_KEY)
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=je(content))


@ROUTER.patch('/train')
async def train_model_handler(r: TrainModelRequest, uid: str = Depends(get_user())) -> JSONResponse:
    """API handler used to handle batch processing
    of model data

    Args:
        r (BatchProcessRequest): [description]
        uid (str, optional): [description]. Defaults to Depends(get_user()).

    Returns:
        JSONResponse: [description]
    """

    LOGGER.debug('received request to batch process data async for user %s', uid)
    # get model metadata from postgres server. return
    # 404 error code if model cannot be found
    model_meta = get_user_model(PG_CREDENTIALS, uid, r.model_id)
    if model_meta is None:
        LOGGER.error('unable to retrieve model %s for user %s', r.model_id, uid)
        return json_response_with_message(status.HTTP_404_NOT_FOUND, 'Cannot find specified model')

    # validate provided input vectors against
    # the schema registered against the model
    invalid_input_points = any(not validate_data_point(x, model_meta.model_schema) for x in r.input_vectors)
    if invalid_input_points:
        LOGGER.error('unable to validate data point(s) against schema %s', model_meta.model_schema)
        return json_response_with_message(status.HTTP_400_BAD_REQUEST, 'Invalid input vector(s)')

    # validate provided output vectors against
    # the schema registered against the model
    invalid_output_points =  any(len(x) != model_meta.output_shape for x in r.output_vectors)
    if invalid_output_points:
        LOGGER.error('unable to validate data point(s) against schema %s', model_meta.model_schema)
        return json_response_with_message(status.HTTP_400_BAD_REQUEST, 'Invalid output vector(s)')

    # insert job into database and generate new event
    job_id = insert_async_job(PG_CREDENTIALS, r.model_id, 0)
    event = {'job_id': str(job_id),
             'event_type': 'model_train',
             'event': {
                 'model_id': str(r.model_id),
                 'user': uid,
                 'epochs': r.epochs,
                 'input_vectors': r.input_vectors,
                 'output_vectors': r.output_vectors}}
    # send event to RabbitMQ broker to trigger worker
    write_to_exchange(MESSAGE_BROKER_URL,
                      JOB_EXCHANGE_NAME,
                      json.dumps(event),
                      JOB_EXCHANGE_TYPE,
                      JOB_ROUTING_KEY)

    content = {'http_code': status.HTTP_201_CREATED,
               'message': 'Successfully queued job',
               'job_id': job_id}
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=je(content))

