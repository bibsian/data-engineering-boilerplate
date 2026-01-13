import time
import json
from datetime import datetime

import pytest

from db import create_engine
from stream_handles import EarthquakeStream

ENGINE = create_engine()

def empty_tbl(name):
    return ENGINE.execute(f"DELETE FROM {name}")

def all_from_tbl(name):
    return ENGINE.execute(f"SELECT * FROM {name}").fetchall()

@pytest.fixture
def setup():
    """ Emptying Dev Table"""
    empty_tbl(EarthquakeStream.TABLE_NAME)
    yield True
    empty_tbl(EarthquakeStream.TABLE_NAME)


@pytest.fixture
def activity():
    return json.dumps({
        'activityType': "EARTHQUAKE",
        'depth': 10,
        'id': "test-id",
        'isCatastrophic': False,
        'latitude': 32.11,
        'longitude': -123.98,
        'magnitude': 3.4,
        'timestamp': datetime.now().isoformat()
    })


def test_insert(setup, activity):
    handler = EarthquakeStream(ENGINE)
    processed = handler.process(activity); time.sleep(1) # lag?
    assert processed # asserts process returned True
    assert all_from_tbl(handler.TABLE_NAME) # asserts record exists
