"""Module containing code used to run tensor flow models"""

import logging
import io
from uuid import UUID
from typing import Union, List, Dict

import h5py
import numpy as np
import pandas as pd
from tensorflow.keras.models import load_model
from tensorflow.python.keras.saving import hdf5_format

from src.services import tensor
from src.logic.utils import parse_base64_file, timer

LOGGER = logging.getLogger(__name__)


@timer
def get_tensorflow_model(model_id: UUID, user: str) -> Union[io.BytesIO, None]:
    """Function used to retrieve and parse
    tensorflow model from Tensor Trigger API

    Args:
        model_id (UUID): ID of model to retrieve
        user (str): user ID

    Returns:
        Union[io.BytesIO, None]: BytesIO instance containing
            model data or None
    """

    # retrieve base64 encoded model data from API
    model = tensor.get_model(model_id, user)
    if model is None:
        LOGGER.error('unable to retrieve model %s', model_id)
        return
    # parse base64 model data into BytesIO instance
    # and attempt to load h5file
    _, buffer = parse_base64_file(model)
    try:
        with h5py.File(buffer, 'r') as h5file:
            network = load_model(h5file)
        return network
    except Exception:
        LOGGER.exception('unable to load tensor flow model')


@timer
def get_job_csv_data(job_id: UUID, user: str) -> Union[np.ndarray, None]:
    """Function used to retrieve CSV input
    data used to run model(s)

    Args:
        job_id (UUID): ID of job
        user (str): user ID

    Returns:
        Union[np.ndarray, None]: numpy array containing data
            else None
    """

    # retrieve base64 encoded model data from API
    raw_data = tensor.get_job_input_data(job_id, user)
    if raw_data is None:
        LOGGER.error('unable to retrieve input data for job %s', job_id)
        return
    # parse base64 model data into BytesIO instance
    # and attempt to load h5file
    _, buffer = parse_base64_file(raw_data)
    try:
        df = pd.read_csv(buffer, header=0)
        return df.values
    except Exception:
        LOGGER.exception('unable to load tensor flow model')


@timer
def run_tensorflow_model(model_id: UUID, job_id: UUID, user: str):
    """Function used to run tensorflow models

    Args:
        model_id (UUID): [description]
        job_id (UUID): [description]
        user (str): [description]
    """

    # get tensorflow model from tensor trigger API
    model = get_tensorflow_model(model_id, user)
    if model is None:
        LOGGER.error('unable to retrieve tensorflow model')
        return

    # get input data from tensor trigger API
    input_data = get_job_csv_data(job_id, user)
    if input_data is None:
        LOGGER.error('unable to retrieve input data')
        return

    try:
        # run model with provided input data
        results = model.predict(input_data)
        return results.tolist()
    except Exception:
        LOGGER.exception('unable to run tensorflow model')


@timer
def train_tensorflow_model(model_id: UUID,
                           user: str,
                           epochs: int,
                           input_vectors: List[Dict[str, float]],
                           output_vectors: List[List[float]]):
    """Function used to run tensorflow models

    Args:
        model_id (UUID): [description]
        job_id (UUID): [description]
        user (str): [description]
    """

    # get tensorflow model from tensor trigger API
    model = get_tensorflow_model(model_id, user)
    if model is None:
        LOGGER.error('unable to retrieve tensorflow model')
        return

    # generate input data for model and convert
    # to numpy array (convert from 1d to 2d)
    input_data = np.array([list(v.values()) for v in input_vectors])
    input_data = input_data.reshape(-1, len(input_data[0]))

    # generate output data for model and convert
    # to numpy array (convert from 1d to 2d)
    output_data = np.array(output_vectors)
    output_data = output_data.reshape(-1, len(output_data[0]))
    try:
        # run model with provided input data
        model.fit(input_data, output_data, epochs=epochs)
        # generate new instance of BytesIO
        # and save model to byes data
        buffer = io.BytesIO()
        with h5py.File(buffer, 'w') as f:
            model.save(f)
        return buffer
    except Exception:
        LOGGER.exception('unable to update tensorflow model')
