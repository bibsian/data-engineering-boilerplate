import os
import json
import logging
import time

import boto3
from kafka_client import create_consumer

logger = logging.getLogger(__name__)

STAGE = os.getenv("STAGE", "dev")


class BronzeConsumerBase:
    def __init__(self, s3_client, bucket, topic, batch_size=1000, t_limit=60):
        self.s3_client = s3_client
        self.bucket = bucket
        self.topic = topic
        self.batch_size = batch_size
        self.t_limit = t_limit
        self.last_flush = time.time()
        self.buffer = []

    def consume(self, message):
        pass # Add to buffer

    def should_flush(self):
        "Check batch size or Time Limit"
        size_reached = len(self.buffer) >= self.batch_size
        time_reached = (time.time() - self.last_flush) >= self.t_limit
        return size_reached or time_reached

    def flush(self):
        self.last_flush = time.time()
        pass # Write buffer to MinIO, clear buffer

    def generate_key(self):
        pass # S3 object key (path) for the batch
