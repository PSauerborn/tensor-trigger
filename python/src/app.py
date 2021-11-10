"""Module containing codebase for cognito wrapper API"""

import logging

from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.utils import json_response_with_message
from src.routers import models, tensor

LOGGER = logging.getLogger(__name__)
APP = FastAPI(title='Tensor Trigger API', version='0.1.0')


@APP.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    content = {'http_code': exc.status_code,
               'message': str(exc.detail)}
    return JSONResponse(status_code=exc.status_code, content=content)


@APP.get('/health_check', summary='Health check endpoint')
async def health_handler() -> JSONResponse:
    """API handler used to serve health
    check response in JSON format
    Returns:
        JSONResponse: JSON response
    """

    LOGGER.debug('received request for health check endpoint')
    return json_response_with_message(status.HTTP_200_OK, 'Service running')

APP.include_router(models.ROUTER, prefix='/models')
APP.include_router(tensor.ROUTER, prefix='/tensor')