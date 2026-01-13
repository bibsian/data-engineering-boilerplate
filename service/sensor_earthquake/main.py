import os
import random
import time

from earthquake_activity import EarthquakeActivity
#from db import create_engine
#from stream_handles import EarthquakeStream


def generate_activity():
    return EarthquakeActivity(
        latitude=random.uniform(32.5121, 42.0126),
        longitude=random.uniform(-124.6509, -114.131),
        depth=random.uniform(5, 100),
        magnitude=random.uniform(1, 9)
    )


# TODO: implement this based on your architecture
def send_activity(activity_str):
    print('>> Earthquake activity is ready to send')
    #handler = EarthquakeStream(ENGINE)
    #processed = handler.process(activity)
    #print('>> Earthquake activity captured')

if __name__ == '__main__':
    while True:
        activity = generate_activity()
        send_activity(str(activity))
        time.sleep(int(random.uniform(2, 10)))
