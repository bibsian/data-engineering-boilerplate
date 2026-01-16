import logging
import os

from kafka import KafkaProducer,KafkaConsumer

logger = logging.getLogger(__name__)

TOPIC_STAGE = os.getenv("STAGE", "dev")


def create_producer():
    """
    All creditials would be stored in AWS's System Manager (parameter store)
    and fetched through boto3 (credentials required to utilize/can
    be injected during container creation and later removed).
    """
    
    return KafkaProducer(
        bootstrap_servers='kafka:9092',
        ackacks='all',
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )

def create_consumer(topic:str):
    return KafkaConsumer(
        topic+TOPIC_STAGE,
        bootstrap_servers='kafka:9092',
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        auto_offset_reset='earliest',
        group_id='minio-consumer-group'
    )
