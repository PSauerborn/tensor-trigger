"""Module containing RabbitMQ functionality"""

import logging

import pika

LOGGER = logging.getLogger(__name__)


def write_to_exchange(message_broker_url: str,
                      exchange_name: str,
                      payload: str,
                      exchange_type: str = '',
                      routing_key: str = '',
                      persistent: bool = False,
                      durable: bool = False,
                      passive: bool = False):
    """Function used to write message over specified
    RabbitMQ exchange

    Args:
        message_broker_url (str): Queue URL of message broker
        exchange_name (str): name of exchange
        exchange_type (str): type of exchange
        payload (str): payload to send over RabbitMQ broker
        persistent (bool, optional): send messages are persistent.
            Defaults to False.
    """

    LOGGER.debug('posting message %s over RabbitMQ server', payload)
    channel, connection = None, None
    try:
        # generate new rabbitmq connection and declare exchange
        connection = pika.BlockingConnection(parameters=pika.URLParameters(message_broker_url))
        channel = connection.channel()
        if exchange_type != '':
            LOGGER.debug('declaring new RabbitMQ exchange %s as type %s', exchange_name, exchange_type)
            channel.exchange_declare(exchange=exchange_name,
                                     exchange_type=exchange_type,
                                     durable=durable,
                                     passive=passive)
        # define message properties and send message over queue url
        message_properties = pika.BasicProperties(delivery_mode=2 if persistent else 1)
        channel.basic_publish(exchange=exchange_name,
                              routing_key=routing_key,
                              body=payload,
                              properties=message_properties)
    except pika.exceptions.AMQPConnectionError:
        LOGGER.exception('unable to connect to RabbitMQ broker')
        raise
    finally:
        if channel is not None:
            channel.close()
        if connection is not None:
            connection.close()