"""Module containing code for tensor trigger worker process"""

import logging
import json
import io
import functools
from uuid import UUID
from typing import Callable

from pydantic import BaseModel, ValidationError

from src.logic.tensor import run_tensorflow_model
from src.logic.rabbit import AMQPExchangeConfig, \
    listen_on_exchange, ack_message
from src.config import MESSAGE_BROKER_URL, EXCHANGE_NAME, \
    EXCHANGE_TYPE, ROUTING_KEY, PG_CREDENTIALS
from src.persistence.postgres import update_job_state
from src.persistence.s3 import upload_s3_file


LOGGER = logging.getLogger(__name__)


class TensorTriggerPayload(BaseModel):

    job_id: UUID
    model_id: UUID
    user: str


def message_handler(channel: object,
                    msg: bytes,
                    connection: object,
                    tag: object,
                    *args, **kwargs):
    """Function used to handle incoming
    AMQP packets

    Args:
        channel (object): [description]
        msg (bytes): [description]
        connection (object): [description]
        tag (object): [description]
    """

    try:
        LOGGER.debug('processing packet %s', msg)
        payload = json.loads(msg)
        # convert event to pydantic model
        event = TensorTriggerPayload(**payload)

        LOGGER.info('processing job %s for user %s', event.job_id, event.user)
        update_job_state(PG_CREDENTIALS, event.job_id, 1)
        # run tensorflow model with specified values
        results = run_tensorflow_model(event.model_id, event.job_id, event.user)
        if results is None:
            LOGGER.exception('unable to complete tensorflow job')
            update_job_state(PG_CREDENTIALS, event.job_id, 3)
        else:
            LOGGER.info('successfully completed job %s', event.job_id)
            output = json.dumps({'output': results})
            # convert json output to BytesIO instance
            # and upload to s3 server for API
            bytes_data = io.BytesIO()
            bytes_data.write(output.encode('utf-8'))
            bytes_data.seek(0)
            upload_s3_file(bytes_data, '/tensor-trigger/output-data' + str(event.job_id))

            # update job state in database with success
            update_job_state(PG_CREDENTIALS, event.job_id, 2)
        ack_message(connection, channel, tag)

    except (json.JSONDecodeError, ValidationError):
        LOGGER.exception('received invalid JSON packet')
        update_job_state(PG_CREDENTIALS, event.job_id, 3)
        ack_message(connection, channel, tag)

    except Exception:
        LOGGER.exception('unable to process payload')
        update_job_state(PG_CREDENTIALS, event.job_id, 3)


def worker_factory() -> Callable:
    """Function used to generate new worker
    instance

    Args:
        queue_url (str): [description]

    Returns:
        Callable: [description]
    """

    exchange_config = AMQPExchangeConfig(**{
        'queue_url': MESSAGE_BROKER_URL,
        'queue_name': ROUTING_KEY,
        'exchange_type': EXCHANGE_TYPE,
        'exchange_name': EXCHANGE_NAME,
        'routing_keys': [ROUTING_KEY],
        'auto_ack': False
    })
    return functools.partial(listen_on_exchange, message_handler, exchange_config)
