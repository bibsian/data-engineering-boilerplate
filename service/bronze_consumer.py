import os
import json
import logging

logger = logging.getLogger(__name__)

STAGE = os.getenv("STAGE", "dev")


class StreamDirectToLake:
    def __init__(self, consumer) -> None:
        self.consumer = consumer

    def insert(self, path):
        pass

    def pre_process(self, data):
        return data

    def transform(self, data):
        return data
