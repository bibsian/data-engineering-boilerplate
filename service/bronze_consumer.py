import datetime
import io
import os
import json
import logging
import time

from kafka import KafkaConsumer


logger = logging.getLogger(__name__)

STAGE = os.getenv("STAGE", "dev")


class BronzeConsumerBase:
    def __init__(self, s3_client
                 ,bucket
                 ,consumer:KafkaConsumer
                 ,batch_size=1000
                 ,t_limit=60):
        self.s3_client = s3_client
        self.bucket = bucket
        self.consumer = consumer
        self.topic_name = self.consumer.topics()[0]
        self.batch_size = batch_size
        self.t_limit = t_limit
        self.last_flush = time.time()
        self.buffer = []

    def consume_batch(self, message):
        for message in self.consumer:
            self.buffer.append(message.value)
            if self.should_flush():
               self.flush()
               self.last_flush = time.time()

    def should_flush(self):
        "Check batch size or Time Limit"
        size_reached = len(self.buffer) >= self.batch_size
        time_reached = (time.time() - self.last_flush) >= self.t_limit
        return size_reached or time_reached

    def flush(self):
        """ Write buffered messages to MinIO S3 """
        batch_data = json.dumps(self.buffer, indent=2).encode('utf-8')
        self.s3_client.put_object(
            bucket_name=self.bucket,
            object_name=self.generate_key(),
            data=io.BytesIO(batch_data),
            length=len(batch_data)
        )
        self.buffer = []  # Clear buffer after flushing

    def generate_key(self):
        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        object_name = (
            f"bronze/{STAGE}/{self.topic_name}/batch_{timestamp}.json")
        return object_name
