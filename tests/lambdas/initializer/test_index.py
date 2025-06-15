
import os
import io
import json
from unittest.mock import patch
import pytest

from lambdas.initializer.index import handler

os.environ['QUEUE_URL'] = 'https://sqs.us-east-1.amazonaws.com/123456789012/fake-queue-url'


@pytest.fixture # this fixture is used to mock the s3_client.get_object method
def csv_content():

    """Fixture to read the CSV file content"""
    csv_file_path = os.path.join(os.path.dirname(__file__), "../../../../docs/2025-06-10-pamphlet_bot.csv")
    with open(csv_file_path, 'r') as f:
        csv_content = f.read()

@pytest.fixture
def s3_event():
    """Fixture providing a mock S3 event"""
    return {'s3_path': 's3://test-bucket/test-file.csv'}

@pytest.fixture
def mock_s3_response(csv_content):
    """Fixture providing a mock S3 get_object response"""
    return {"Body": BytesIO(csv_content.encode('utf-8'))}

@pytest.fixture
def mock_sqs_response():
    """Fixture providing a mock SQS send_message response"""
    return {'MessageId': '1234567890'}

@patch('lambdas.initializer.index.sqs_client')
@patch('lambdas.initializer.index.s3_client')
def test_handler_s3_get_object_called_correctly(
    mock_send_message,
    mock_get_object,
    s3_event,
    mock_s3_response,
    mock_sqs_response):
    """Test that s3_client.get_object is called with the correct arguments"""

    mock_get_object.return_value = mock_s3_response
    mock_send_message.return_value = mock_sqs_response

    handler(s3_event, None)

    # Verify S3 get_object was called
    mock_get_object.assert_called_once()

@patch('lambdas.initializer.index.s3_client.get_object')
@patch('lambdas.initializer.index.sqs_client.send_message')
def test_handler_sqs_message_content(mock_send_message, mock_get_object, s3_event, mock_s3_response, mock_sqs_response):
    """Test that SQS message content send by the handler"""

    mock_get_object.return_value = mock_s3_response
    mock_send_message.return_value = mock_sqs_response

    handler(s3_event, None)

    # Get all message bodies sent to SQS
    sent_messages = []
    for call in mock_send_message.call_args_list:
        kwargs = call.kwargs
        message_body = json.loads(kwargs['MessageBody'])
        sent_messages.append(message_body)

    # Verify the message structure for all sent messages
    for message in sent_messages:
        assert isinstance(message, dict), "Each message should be a dictionary"
        assert 'test_case' in message, "Each message should have a 'test_case' key"
        assert 'step' in message, "Each message should have a step field"

if __name__ == '__main__':
    pytest.main([__file__])
