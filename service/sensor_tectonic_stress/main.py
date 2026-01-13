import os
import random
import time

#from kafka_client import create_producer, TOPIC_STR
from tectonic_stress_activity import TectonicStressActivity


def generate_activity():
    sensor_has_malfunctioned = random.uniform(1, 5) <= 1
    stress_mag = None if sensor_has_malfunctioned else random.uniform(100, 100000)
    return TectonicStressActivity(stress_magnitude=stress_mag)


def send_activity(producer, activity_str):
    print('>> Tectonic stress activity is ready to send')
    #producer.send(f'tectonic-stress-raw-{TOPIC_STR}', value=activity_str)
    #producer.flush()
    print('>> Tectonic stress captured')
    return

if __name__ == '__main__':
    while True:
        #producer = create_producer()
        activity = generate_activity()
        send_activity(None, str(activity))
        time.sleep(1)
