import os
import unittest
from unittest.mock import patch
from processor.index import handler
import json



os.environ['QUEUE_URL'] = 'https://sqs.us-east-1.amazonaws.com/123456789012/fake-queue-url'
os.environ['FIREHOSE_NAME'] = 'TestFirehoseName'


from lambdas.processor import index


class TestProcessorLambda(unittest.TestCase):
    @patch('processor.index.index.sqs_client')
    @patch('processor.index.index.firehose_client')
    @patch('processor.index.index.lex_client')
    def test_handler(self, mock_lex_client, mock_firehose_client, mock_sqs_client):

        # Mock SQS event receive_message
        event = {
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

        # Mock Lex response
        mock_lex_client.recognize_text.return_value = {
            'messages': [{'content': 'Hi'}],
            'sessionState': {
                'intent': {
                    'intent': {'name': 'GreetingIntent', 'state': 'Fulfilled'},
                    'sessionAttributes': {'key': 'value'}
                }
            }
        }

        # Call the lambda handler
        handler(event, None)

        # Assertions
        mock_lex_client.recognize_text.asser_called_once()
        mock_firehose_client.put_record.assert_called_once_with(
            DeliveryChannel=os.environ['FIREHOSE_NAME'],
            Record={
                'Data': json.dumps({
                    'test_case': '1',
                    'step': '1',
                    'utterance': "",
                    "session_attributes": "",
                    "expected_response": "",
                    "expected_intent": "",
                    "expected_state": "Fulfilled",
                    "bot_id": "TODO", # TODO: Replace with actual bot_id
                    "alias_id": "TODO", # TODO: Replace with actual alias_id
                    "locale_id": "en_US", # TODO: Replace with actual locale_id
                    "response": "Hi",
                    "actual_intent": "GreetingIntent",
                    "actual_state": "Fulfilled",
                    "test_result": None,
                    "test_explanation": None
                })+ '\n'
            }
        )
        mock_sqs_client.delete_message.assert_called_once_with(
            QueueUrl=os.environ['QUEUE_URL'],
            ReceiptHandle='mockReceiptHandle'
        )

if __name__ == '__main__':
    unittest.main()
