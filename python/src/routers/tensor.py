"""Module containing API router for tensor
trigger functionality"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from src.utils import get_user,json_response_with_message
from src.persistence.postgres import get_user_model
from src.persistence.s3 import retrieve_s3_file
from src.config import PG_CREDENTIALS
from src.logic.tensor import validate_data_point, run_model, \
    validate_upload_content
from src.models.tensor import ProcessRequest


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
    model_meta = get_user_model(PG_CREDENTIALS, uid, r.model_id)
    if model_meta is None:
        LOGGER.error('unable to retrieve model %s for user %s', r.model_id, uid)
        return json_response_with_message(status.HTTP_404_NOT_FOUND, 'Cannot find specified model')

    # validate datapoint against specified input vector
    if not validate_data_point(r.input_vector, model_meta.model_schema):
        LOGGER.error('unable to validate data point %s against schema %s', r.input_vector, model_meta.model_schema)
        return json_response_with_message(status.HTTP_400_BAD_REQUEST, 'Invalid input vector')

    # retrieve hd5 file from s3 storage
    s3_data = retrieve_s3_file('/tensor-trigger/' + str(r.model_id))
    # convert to tensorflow model and run results
    result = run_model(s3_data, r.input_vector)
    if result is None:
        LOGGER.error('unable to run model %s', r.model_id)
        return json_response_with_message(status.HTTP_500_INTERNAL_SERVER_ERROR, 'Internal server error')

    content = {'http_code': status.HTTP_200_OK, 'output': float(result)}
    return JSONResponse(status_code=status.HTTP_200_OK, content=content)



