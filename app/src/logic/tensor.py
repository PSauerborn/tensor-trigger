"""Module containing logic for tensorflow functionality"""

import logging
import io
from typing import Dict, Any, Union
from collections import namedtuple

import h5py
import numpy as np
import pandas as pd
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

    for key, item in schema.items():
        if key not in data:
            return False
        # get convertor based on data type
        # and attempt to cast to specified
        # type. Return false if data point
        # cannot be verified
        var_type = item.get('var_type')
        convertor = TYPE_CONVERTORS.get(var_type.upper())
        try:
            convertor(data[key])
        except Exception:
            LOGGER.exception('unable to cast value %s to type %s', data[key], var_type)
            return False
    return True


def _get_expected_input_shape(model) -> int:
    """Function used to extract the expected
    input shape from a tensorflow model

    Args:
        model ([type]): [description]

    Returns:
        int: [description]
    """

    try:
        layers = model.get_config()['layers']
        input_layer_config = layers[0]['config']
        return input_layer_config['batch_input_shape'][1]
    except (KeyError, IndexError):
        pass

def _get_expected_output_shape(model) -> int:
    """Function used to extract the expected
    input shape from a tensorflow model

    Args:
        model ([type]): [description]

    Returns:
        int: [description]
    """

    try:
        layers = model.get_config()['layers']
        input_layer_config = layers[len(layers) - 1]['config']
        return input_layer_config.get('units')
    except (KeyError, IndexError):
        pass


ModelInputOutput = namedtuple('ModelInputOutput', ['input_shape', 'output_shape'])

def validate_upload_content(content: io.BytesIO, schema: Dict[str, str]):
    """Function used to validate uploaded
    file contents can be parsed to tensorflow model

    Args:
        content (io.BytesIO): [description]
    """

    try:
        with h5py.File(content, 'r') as h5file:
            model = load_model(h5file)
        # determine expected input length from model and
        # raise exception is schema does not fit expected
        # length
        expected_input_shape = _get_expected_input_shape(model)
        if expected_input_shape != len(schema.keys()):
            LOGGER.error('unable to validate inputs: expected length does not match schema: expected %s got %s',
                         expected_input_shape, len(schema.keys()))
            raise ValueError

        # evaluate expected output shape
        expected_output_shape = _get_expected_output_shape(model)
        return ModelInputOutput(input_shape=expected_input_shape,
                                output_shape=expected_output_shape)
    except Exception:
        LOGGER.exception('unable to validate input model')
        raise


def _format_input_vector(input_vector: Dict[str, str], schema: Dict[str, dict]) -> np.ndarray:
    """Function used to format input vector
    into required shape and size

    Args:
        input (Dict[str, str]): [description]

    Returns:
        np.ndarray: [description]
    """

    flattened_schema = [{'name': k, 'var_type': v['var_type'], 'index': v['index']}
                         for k, v in schema.items()]
    # sort schema by index to ensure that data values are inserted in
    # correct order into model
    sorted_schema = sorted(flattened_schema, key=lambda row: row['index'])

    # construct sorted input vector
    sorted_input_vector = []
    for item in sorted_schema:
        var_name = item['name']
        sorted_input_vector.append(input_vector[var_name])

    # transform into array and reshape to be 2 dimensional
    array = np.array(sorted_input_vector)
    return array.reshape(-1, len(schema.keys()))


def run_model(model_file: io.BytesIO,
              input_vector: Dict[str, float],
              schema: Dict[str, dict]) -> Union[float, None]:
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
        input_vector = _format_input_vector(input_vector, schema)
        results = network.predict(input_vector)
        return results.tolist() if results.shape[0] > 0 else None
    except Exception:
        LOGGER.exception('unable to run model with input vector %s', input_vector)


def _format_input_vector_batch(input_vectors: Dict[str, str], schema: Dict[str, dict]) -> np.ndarray:
    """Function used to format input vector
    into required shape and size

    Args:
        input (Dict[str, str]): [description]

    Returns:
        np.ndarray: [description]
    """

    flattened_schema = [{'name': k, 'var_type': v['var_type'], 'index': v['index']}
                         for k, v in schema.items()]
    # sort schema by index to ensure that data values are inserted in
    # correct order into model
    sorted_schema = sorted(flattened_schema, key=lambda row: row['index'])

    def sort_input_vector(v: dict) -> dict:
        # construct sorted input vector
        sorted_input_vector = []
        for item in sorted_schema:
            var_name = item['name']
            sorted_input_vector.append(v[var_name])
        return sorted_input_vector

    batch = [sort_input_vector(v) for v in input_vectors]
    # transform into array and reshape to be 2 dimensional
    array = np.array(batch)
    return array.reshape(-1, len(schema.keys()))


def run_model_batched(model_file: io.BytesIO,
                      input_vectors: Dict[str, float],
                      schema: Dict[str, dict]) -> Union[float, None]:
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
        input_vectors = _format_input_vector_batch(input_vectors, schema)
        results = network.predict(input_vectors)
        return results.tolist() if results.shape[0] > 0 else None
    except Exception:
        LOGGER.exception('unable to run model with input vectors')


def validate_csv_file(contents: io.BytesIO, schema: Dict[str, dict]) -> bool:
    """Function used to validate CSV input for
    batch processing

    Args:
        contents (io.BytesIO): bytes data from CSV file
        schema (Dict[str, dict]): model schema to use
            for validation

    Returns:
        bool: [description]
    """

    try:
        df = pd.read_csv(contents, header=0)
        # get columns from dataframe
        cols = list(df.columns)
        if any(key not in schema for key in cols):
            return False

        return len(cols) == len(schema)

    except Exception:
        LOGGER.exception('unable to parse CSV file into dataframe')
    return False