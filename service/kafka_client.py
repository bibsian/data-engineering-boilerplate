import logging
import os

from kafka import KafkaProducer

logger = logging.getLogger(__name__)

STAGE = os.getenv("STAGE", "dev")
if "dev" in STAGE:
    TOPIC_STR = "dev"
else:
    TOPIC_STR = "prod"


def create_producer():
    """
    All creditials would be stored in AWS's System Manager (parameter store)
    and fetched through boto3 (credentials required to utilize/can
    be injected during container creation and later removed).
    """
    
    return KafkaProducer(
        bootstrap_servers='kafka:9092',
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )