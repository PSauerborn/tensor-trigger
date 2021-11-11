"""Module containing base AMQP worker used to connect
to RabbitMQ queue/exchange"""

import logging
import time
import threading
import functools
from typing import Callable, List

import pika
from pika.exceptions import ConnectionClosed, StreamLostError, \
    AMQPConnectionError
from pydantic import BaseModel


LOGGER = logging.getLogger(__name__)
WORKER_THREADS = []


class AMQPExchangeConfig(BaseModel):
    """Dataclass containing AMQP exchange
    configuration settings

    Arguments:
        queue_url: str connection string for RabbitMQ
            broker in amqp://<user>:<pass>@<host>:<port>/<vhost>
            format
        queue_name: str name of queue to connect to. random
            queue name is generated if blank
        exchange_name: str name of exchange
        exchange_type: str type of exchange. defaults to
            fanout
        durable: bool exchange is created as durable if set
            to true. default is false
        prefetch_count: int number of messages to pre-fetch.
            defaults to 1
        reconnection_interval: int number of seconds to
            wait between reconnections. defaults to 15
        auto_ack: bool messages are auto-acknowledged
            if set to true. defaults to true
    """

    queue_url: str
    queue_name: str = ''
    exchange_name: str
    exchange_type: str = 'fanout'
    routing_keys: List[str] = [None]
    durable: bool = False
    prefetch_count: int = 1
    reconnection_interval: int = 15
    auto_ack: bool = True


def ack_message(connection: object, channel: object, delivery_tag: object):
    """Function used to acknowledge that worker has received
    message. Note that this should be called explicitly if
    the auto_ack parameter is not set to True"""

    def ack(chan, tag):
        if chan.is_open:
            chan.basic_ack(tag)
        else:
            LOGGER.warning('unable to ack message: channel already closed')
    # add message acknowledgement as threadsafe
    # callback to connection
    cb = functools.partial(ack, channel, delivery_tag)
    connection.add_callback_threadsafe(cb)


def on_message(handler: Callable,
               channel: object,
               method_frame: object,
               properties: object,
               body: str,
               args: tuple):
    """Function called to handle rabbitMQ messages. An instance
    of the process_payload function is added to the global thread
    count and processed on a separate thread to prevent the RabbitMQ
    server from ejecting connection"""

    (connection, WORKER_THREADS) = args
    delivery_tag = method_frame.delivery_tag
    t = threading.Thread(target=handler,
                         args=(channel, body, connection, delivery_tag, properties, args))
    t.start()
    WORKER_THREADS.append(t)


def listen_on_exchange(handler: Callable,
                       config: AMQPExchangeConfig,
                       handle_errors: bool = True):
    """Function used to generate RabbitMQ exchange
    and listen for messages. The listener first
    declares an exchange, and then binds a queue
    to the declared exchange. If no queue configuration
    is provided, an exclusive queue is generated

    Arguments:
        handler: Callable function used to handle
            incoming messages
        config: AMQPExchangeConfig configuration settings
            for exchange and queue
        handler_errors: bool connection errors are handled
            by listener if set to true
    """

    while True:
        try:
            with pika.BlockingConnection(parameters=pika.URLParameters(config.queue_url)) as connection:
                # create channel and declare exchange using specified config
                channel = connection.channel()
                channel.exchange_declare(exchange=config.exchange_name,
                                         exchange_type=config.exchange_type,
                                         durable=config.durable)

                # generate new queue to listen on and bind to exchange
                result = channel.queue_declare(queue=config.queue_name,
                                               exclusive=config.queue_name == '')
                # if queue is specified, use queue name to bind
                # else get randomly generate queue name
                if not config.queue_name:
                    queue_name = result.method.queue
                else:
                    queue_name = config.queue_name

                # bind new queue to exchange using all provided
                # routing keys
                for key in config.routing_keys:
                    channel.queue_bind(exchange=config.exchange_name,
                                       queue=queue_name,
                                       routing_key=key)

                # set prefetch count to 1 to avoid clearing all message from queue
                channel.basic_qos(prefetch_count=config.prefetch_count)
                # define message callback and start listening on queue
                on_message_callback = functools.partial(on_message, handler, args=(connection, WORKER_THREADS))
                channel.basic_consume(on_message_callback=on_message_callback,
                                      queue=queue_name,
                                      auto_ack=config.auto_ack)
                channel.start_consuming()

        # catch connection errors
        except (ConnectionClosed, StreamLostError, AMQPConnectionError):
            if not handle_errors:
                raise
            LOGGER.exception('disconnected from server. waiting %s seconds before reconnection',
                             config.reconnection_interval)
            # wait for certain amount of time before attempting to reconnect to server
            time.sleep(config.reconnection_interval)

    channel.stop_consuming()