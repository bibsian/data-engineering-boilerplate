import os
import random
import time

from tectonic_stress_activity import TectonicStressActivity


def generate_activity():
    sensor_has_malfunctioned = random.uniform(1, 5) <= 1
    stress_mag = None if sensor_has_malfunctioned else random.uniform(100, 100000)
    return TectonicStressActivity(stress_magnitude=stress_mag)


# TODO: implement this based on your architecture
def send_activity(activity_str):
    print('>> Tectonic stress activity is ready to send')


if __name__ == '__main__':
    while True:
        activity = generate_activity()
        send_activity(str(activity))
        time.sleep(1)
