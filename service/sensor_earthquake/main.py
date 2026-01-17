import json
import os
import random
import time

from earthquake_activity import EarthquakeActivity
from kafka_client import create_producer, TOPIC_STAGE


def generate_activity():
    return EarthquakeActivity(
        latitude=random.uniform(32.5121, 42.0126),
        longitude=random.uniform(-124.6509, -114.131),
        depth=random.uniform(5, 100),
        magnitude=random.uniform(1, 9)
    )


def send_activity(producer, activity_str):
    print('>> Earthquake activity is ready to send')
    producer.send(f'earthquake-raw-{TOPIC_STAGE}', value=activity_str)
    producer.flush()
    print('>> Earthquake activity captured')
    return True

if __name__ == '__main__':
    while True:
        producer = create_producer()
        activity = generate_activity()
        send_activity(producer, str(activity))
        time.sleep(int(random.uniform(60, 120)))
