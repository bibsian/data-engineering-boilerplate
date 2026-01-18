import json
from unittest.mock import Mock,MagicMock

import pytest

from bronze_consumer import BronzeConsumerBase


@pytest.fixture
def mock_s3_client():
    return MagicMock()

@pytest.fixture
def mock_consumer():
    consumer = MagicMock()
    consumer.topics.return_value = ["earthquake-raw"]
    return consumer

@pytest.fixture
def bronze_consumer(mock_s3_client, mock_consumer):
    return BronzeConsumerBase(
        s3_client=mock_s3_client,
        bucket="bronze",
        consumer=mock_consumer,
        batch_size=3,  # small for testing
        t_limit=60
    )

def test_consume_batch_flush_by_size(bronze_consumer, mock_s3_client, mock_consumer):
    # Mock messages
    messages = [
        Mock(offset=i, timestamp=1234567890+i, key=None, value=json.dumps({"data": i}).encode())
        for i in range(5)
    ]
    mock_consumer.__iter__.return_value = iter(messages)

    bronze_consumer.consume_batch()

    assert mock_s3_client.put_object.call_count == 1

    # Check the first flush
    first_call_args = mock_s3_client.put_object.call_args_list[0][1]
    assert first_call_args['bucket_name'] == "bronze"
    assert len(json.loads(first_call_args['data'].getvalue())) == 3
