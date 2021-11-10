"""Module containing config settings"""

import logging
import os

from typing import Any

from src.persistence.postgres import PostgresCredentials

LOGGER = logging.getLogger(__name__)


TRUE_CONVERSIONS = ['true', 't', '1']

def override_value(key: str, default: Any, secret: bool = False) -> Any:
    """Helper function used to override local configuration
    settings with values set in environment variables
    Arguments:
        key: str name of environment variable to override
        default: Any default value to use if not set
        secret: bool hide value from logs if True
    Returns:
        default value if not set in environs, else value from
            environment variables
    """

    value = os.environ.get(key.upper(), None)
    if value is not None:
        LOGGER.info('overriding variable %s with value %s', key, value if not secret else '*' * 5)

        # cast to boolean if default is of instance boolean
        if isinstance(default, bool):
            LOGGER.info('default value for %s is boolean. casting to boolean', key)
            value = value.lower() in TRUE_CONVERSIONS
    else:
        value = default
    return type(default)(value)

LOG_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARN,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}

LOG_LEVEL = LOG_LEVELS.get(override_value('log_level', 'INFO'), logging.DEBUG)
logging.basicConfig(level=LOG_LEVEL)

for logger in ('boto3', 'botocore'):
    logging.getLogger(logger).setLevel(logging.WARNING)
logging.getLogger('tensorflow').setLevel(logging.ERROR)


POSTGRES_HOST = override_value('POSTGRES_HOST', 'localhost')
POSTGRES_PORT = override_value('POSTGRES_PORT', 5432)
POSTGRES_DB = override_value('POSTGRES_DB', 'tensor_trigger')
POSTGRES_USER = override_value('POSTGRES_USER', 'tensor_trigger')
POSTGRES_PASSWORD = override_value('POSTGRES_PASSWORD', '', secret=True)

PG_CREDENTIALS = PostgresCredentials(**{
    'PG_HOST': POSTGRES_HOST,
    'PG_DATABASE': POSTGRES_DB,
    'PG_PORT': POSTGRES_PORT,
    'PG_USER': POSTGRES_USER,
    'PG_PASSWORD': POSTGRES_PASSWORD
})