"""Entrypoint application for worker"""

import logging

from src.worker import worker_factory

LOGGER = logging.getLogger(__name__)

if __name__ == '__main__':

    worker = worker_factory()
    worker()