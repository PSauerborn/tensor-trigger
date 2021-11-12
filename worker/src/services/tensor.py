"""Module containing code to connect to
downstream servies"""

import logging
from uuid import UUID

import requests

from src.config import TENSOR_TRIGGER_API_URL


LOGGER = logging.getLogger(__name__)


def get_job_input_data(job_id: UUID, user: str) -> str:
    """Function used to retrieve job input
    data from Tensor Trigger API

    Args:
        job_id (UUID): [description]
        user (str): [description]

    Returns:
        str: [description]
    """

    url = TENSOR_TRIGGER_API_URL + '/tensor-trigger/jobs/{}/content'.format(job_id)
    try:
        r = requests.get(url, headers={'X-Authenticated-Userid': user})
        LOGGER.debug('received response %s from API', r.text)
        r.raise_for_status()

        return r.json().get('job')

    except requests.HTTPError:
        LOGGER.exception('unable to retrieve job data from API')


def get_model(model_id: UUID, user: str) -> str:
    """Function used to retrieve tensorflow
    model from Tensor Trigger API

    Args:
        model_id (UUID): [description]
        user (str): [description]

    Returns:
        str: [description]
    """

    url = TENSOR_TRIGGER_API_URL + '/tensor-trigger/models/{}/content'.format(model_id)
    try:
        r = requests.get(url, headers={'X-Authenticated-Userid': user})
        LOGGER.debug('received response %s from API', r.text)
        r.raise_for_status()

        return r.json().get('model')

    except requests.HTTPError:
        LOGGER.exception('unable to retrieve model data from API')
