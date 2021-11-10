"""Module containing logic for tensorflow functionality"""

import logging
import io
from typing import Dict, Any, Union

import h5py
import numpy as np
from tensorflow.keras.models import load_model


LOGGER = logging.getLogger(__name__)


ALLOWED_TYPES = [
    'INT',
    'FLOAT'
]


def is_valid_model_schema(schema: Dict[str, str]) -> bool:
    """

    Args:
        schema (Dict[str, str]): dict containing model schema

    Returns:
        bool: True if schema is valid else false
    """

    return all(s.upper() in ALLOWED_TYPES for s in schema.values())


TYPE_CONVERTORS = {
    'INT': lambda x: int(x),
    'FLOAT': lambda x: float(x)
}

def validate_data_point(data: Dict[str, Any], schema: Dict[str, str]) -> bool:
    """Function used to validate input data
    against a given schema

    Args:
        data (Dict[str, Any]): [description]
        schema (Dict[str, str]): [description]

    Returns:
        bool: [description]
    """

    for key, data_type in schema.items():
        if key not in data:
            return False
        # get convertor based on data type
        # and attempt to cast to specified
        # type. Return false if data point
        # cannot be verified
        convertor = TYPE_CONVERTORS.get(data_type.upper())
        try:
            convertor(data[key])
        except Exception:
            LOGGER.exception('unable to cast value %s to type %s', data[key], data_type)
            return False
    return True

def validate_upload_content(content: io.BytesIO):
    """Function used to validate uploaded
    file contents can be parsed to tensorflow model

    Args:
        content (io.BytesIO): [description]
    """

    try:
        with h5py.File(content, 'r') as h5file:
            load_model(h5file)
    except Exception:
        LOGGER.exception('unable to validate input model')
        raise

def _format_input_vector(input_vector: Dict[str, str]) -> np.ndarray:
    """Function used to format input vector
    into required shape and size

    Args:
        input (Dict[str, str]): [description]

    Returns:
        np.ndarray: [description]
    """

    input_vector = list(input_vector.values())
    return np.array(input_vector).reshape(-1, len(input_vector))

def run_model(model_file: io.BytesIO, input_vector: Dict[str, float]) -> Union[float, None]:
    """Function used to run model via model
    file

    Args:
        model_file (io.BytesIO): file content

    Returns:
        float: [description]
    """

    try:
        with h5py.File(model_file, 'r') as h5file:
            network = load_model(h5file)
        # get run results from model. note that
        # the input vector is cast to the format
        # required by the model schema
        input_vector = _format_input_vector(input_vector)
        results = network.predict(input_vector)

        return next(iter(results.flat)) if results.shape[0] > 0 else None
    except Exception:
        LOGGER.exception('unable to run model with input vector %s', input_vector)