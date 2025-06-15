import os
from unittest.mock import patch
import json
import pytest

from lambdas.processor.index import handler


os.environ['QUEUE_URL'] = 'https://sqs.us-east-1.amazonaws.com/123456789012/fake-queue-url'
os.environ['FIREHOSE_NAME'] = 'TestFirehoseName'


@pytest.fixture
def sqs_event():
    """Fixture providing a mock SQS event"""
    return {
            'Records': [
                {
                    'messageId': '234234-234-234-234fsdgf2434',
                    'receiptHandle': 'mockReceiptHandle',
                    'body': json.dumps([
                        {
                            'test_case': '1',
                            'step': '1',
                            'utterance': "",
                            "session_attributes": "",
                            "expected_response": "",
                            "expected_intent": "",
                            "expected_state": "Fulfilled",
                            "bot_id": "TODO", # TODO: Replace with actual bot_id
                            "alias_id": "TODO", # TODO: Replace with actual alias_id
                            "locale_id": "en_US"
                        }
                    ]),
                    'attributes': {
                        'ApproximateReceiveCount': '13',
                        'AWSTraceHeader': 'TODO',
                        'SentTimestamp': 'TODO',
                        'SenderId': 'TODO',
                        'ApproximateFirstReceiveTimestamp': 'TODO',
                    },
                    'messageAttributes': {},
                    'md5OfBody': 'TODO',
                    'eventSource': 'aws:sqs',
                    'eventSourceARN': 'TODO',
                    'awsRegion': 'us-east-1',
                }
            ]
        }

@pytest.fixture
def mock_lex_response():
    """Fixture providing a mock Lex response"""
    return {
        'messages': [{'content': 'Hi'}],
        'sessionState': {
            'intent': {
                    'intent': {'name': 'GreetingIntent', 'state': 'Fulfilled'},
                    'sessionAttributes': {'key': 'value'}
                }
            }
        }

@pytest.fixture
def expected_firehose_data():
    """Fixture providing expected Firehose data"""
    return {
        'test_case': '1',
        'step': '1',
        'utterance': '',
        'session_attributes': '',
        'expected_response': '',
        'expected_intent': '',
        'expected_state': 'Fulfilled',
        'bot_id': 'TODO',
        'alias_id': 'TODO',
        'locale_id': 'en_US',
        'response': 'Hi',
        'actual_intent': 'GreetingIntent',
        'actual_state': 'Fulfilled',
        'test_result': None,
        'test_explanation': None
    }

@patch('lambdas.processor.index.sqs_client')
@patch('lambdas.processor.index.firehose_client')
@patch('lambdas.processor.index.lex_client')
def test_handler(mock_lex_client, mock_firehose_client, mock_sqs_client, sqs_event, mock_lex_response, expected_firehose_data):
    """Test that the handler processes the event correctly"""

    # Call the lambda handler
    handler(sqs_event, None)

    # Setup mocks
    mock_lex_client.recognize_text.return_value = mock_lex_response

    handler(sqs_event, None)

    # Assertions
    mock_lex_client.recognize_text.assert_called_once_with(
        DeliveryStreemName=os.environ['FIREHOSE_NAME'],
        Record={'Data': json.dumps(expected_firehose_data) + '\n'}
    )
    mock_sqs_client.delete_message.assert_called_once_with(
        QueueUrl=os.environ['QUEUE_URL'],
        ReceiptHandle='mockReceiptHandle'
    )

if __name__ == '__main__':
    pytest.main([__file__])
