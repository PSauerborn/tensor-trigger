"""Module containing code for tensor trigger worker process"""

import logging
import json
import io
import functools
from uuid import UUID
from typing import Callable

from pydantic import ValidationError

from src.models.events import TensorTriggerPayload, ModelRunEvent, \
    ModelTrainEvent
from src.logic.tensor import run_tensorflow_model, train_tensorflow_model
from src.logic.rabbit import AMQPExchangeConfig, \
    listen_on_exchange, ack_message
from src.config import MESSAGE_BROKER_URL, EXCHANGE_NAME, \
    EXCHANGE_TYPE, ROUTING_KEY, PG_CREDENTIALS
from src.persistence.postgres import update_job_state
from src.persistence.s3 import upload_s3_file


LOGGER = logging.getLogger(__name__)


def handle_model_run(job_id: UUID, e: ModelRunEvent):
    """Function used to handle model run
    events

    Args:
        job_id (UUID): ID of job
        e (ModelRunEvent): Event containing
            event details
    """

    # run tensorflow model with specified values
    results = run_tensorflow_model(e.model_id, job_id, e.user)
    if results is None:
        LOGGER.exception('unable to complete tensorflow job')
        update_job_state(PG_CREDENTIALS, job_id, 3)

    else:
        LOGGER.info('successfully completed job %s', job_id)
        output = json.dumps({'output': results})
        # convert json output to BytesIO instance
        # and upload to s3 server for API
        bytes_data = io.BytesIO()
        bytes_data.write(output.encode('utf-8'))
        bytes_data.seek(0)
        upload_s3_file(bytes_data, '/tensor-trigger/output-data' + str(job_id))

        # update job state in database with success
        update_job_state(PG_CREDENTIALS, job_id, 2)


def handle_model_update(job_id: UUID, e: ModelTrainEvent):
    """Function used to handle model run
    events

    Args:
        job_id (UUID): ID of job
        e (ModelRunEvent): Event containing
            event details
    """

    # run tensorflow model with specified values
    new_model = train_tensorflow_model(e.model_id, e.user, e.epochs, e.input_vectors, e.output_vectors)
    if new_model is None:
        LOGGER.exception('unable to complete tensorflow job')
        update_job_state(PG_CREDENTIALS, job_id, 3)
    else:
        LOGGER.info('successfully completed job %s', job_id)
        new_model.seek(0)
        # upload new model to S3 bucket
        upload_s3_file(new_model, '/tensor-trigger/' + str(e.model_id))
        # update job state in database with success
        update_job_state(PG_CREDENTIALS, job_id, 2)


EVENT_HANDLERS = {
    'model_run': handle_model_run,
    'model_train': handle_model_update
}

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

        # convert event to pydantic model and
        # validate event payload based on event type
        e = TensorTriggerPayload(**payload)

        LOGGER.info('processing event %s', e)
        update_job_state(PG_CREDENTIALS, e.job_id, 1)
        # retrieve event handler based on event
        # type and execute
        handler = EVENT_HANDLERS.get(e.event_type)
        handler(e.job_id, e.event)

        # acknowledge message with RabbitMQ server
        ack_message(connection, channel, tag)

    except (json.JSONDecodeError, ValidationError):
        LOGGER.exception('received invalid JSON packet')
        ack_message(connection, channel, tag)

    except Exception:
        LOGGER.exception('unable to process payload')
        update_job_state(PG_CREDENTIALS, e.job_id, 3)


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
