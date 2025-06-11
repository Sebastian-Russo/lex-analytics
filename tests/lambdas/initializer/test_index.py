
import os
import io
import json
from unittest.mock import patch
import unittest

# Is this import possibel because of the same directory structure?
from lambdas.initializer import handler

os.environ['QUEUE_URL'] = 'https://sqs.us-east-1.amazonaws.com/123456789012/fake-queue-url'



class TestInitializerLambda(unittest.TestCase):
    @patch('initializer.index.s3_client.get_object')
    @patch('initializer.index.sqs_client.send_message')
    def test_handler(self, mock_send_message, mock_get_object):
        # Read the CSV files content
        csv_file_path = os.path.join(os.path.dirname(__file__), "../../../../docs/2025-06-10-pamphlet_bot.csv")
        with open(csv_file_path, 'r') as f:
            csv_content = f.read()

        mock_get_object.return_value = {
            'Body': io.BytesIO(csv_content.encode('utf-8')) # Mocked as a file-like object
        }

        # Mock SQS send_message
        mock_send_message.return_value = {
            'MessageId': '12345'
        }

        # Mock event containing the S3 path
        event = {'s3_path': 's3://test-bucket/test-cases/2025-06-10-pamphlet_bot.csv'}

        # Call the lambda handler
        response = handler(event, None)

        # Assertions
        self.assertEqual(mock_send_message.call_count, 2
        ) # Ensure 50 test cases were sent to SQS (based on the CSV file)
        self.assertEqual(response['statusCode'], 200)
        self.assertEqual(response['Message'], 'Processing complete')

        # Verify SQS messages
        for call in mock_send_message.call_args_list:
            kwargs = call.kwargs
            message_body = json.loads(kwargs['MessageBody'])
            first = message_body[0]
            self.assertIn('Test Case', first) # Ensure the message contains the 'Test Case' key
            self.assertIn('Step', first) # Ensure the message contains the 'Step' key

if __name__ == '__main__':
    unittest.main()
