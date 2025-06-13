# initializer.py
"""
This lambda function is responsible for initializing the Lex Analytics pipeline.
It takes an S3 path to a CSV file as input and groups the records by test_case.
"""

import logging
import os
import boto3
import csv
import json
from collections import defaultdict
import datetime

# Configure logging
logging.basicConfig(level=os.environ.get('LOGGING_LEVEL', 'DEBUG'))
logger = logging.getLogger(__name__) # __name__ is the name of the module

# Initialize AWS clients
s3_client = boto3.client('s3')
sqs_client = boto3.client('sqs')

# Environment variables
QUEUE_URL = os.getenv('QUEUE_URL')

# Event will be CSV as plain text
def handler(event, context):
    """
    Expects event with the following keys:
    's3_path': An S3 path ot the CSV file. Format: s3://bucket/key
    """

    logger.debug('Event Received: %s', event)

    test_run = datetime.datetime.now().isoformat()

    # Extract bucket and key from the s3_path
    s3_path = event.get('s3_path')
    if not s3_path:
        raise ValueError('Missing s3_path in event', s3_path)

    if not s3_path.startswith('s3://'):
        raise ValueError('s3_path must start with s3://', s3_path)

    bucket, key = s3_path[5:].split('/', 1) # s3_path[5:] removes the 's3://' prefix

    # Download the CSV file from S3
    logger.info('Downloading CSV file from S3 bucket: %s, key: %s', bucket, key)
    response = s3_client.get_object(Bucket=bucket, Key=key)
    csv_content = response['Body'].read().decode('utf-8')
    logger.info('CSV file downloaded successfully: %s', s3_path)

    # Parse the CSV file and group records by test_case
    grouped_tests = defaultdict(list) # Initialize an empty dictionary to store grouped tests
    csv_reader = csv.DictReader(csv_content.splitlines())
    for row in csv_reader:
        test_number = row['test_case']
        row['test_run'] = test_run
        row['s3_path'] = s3_path
        grouped_tests[test_number].append(row)

    logger.info('Grounded tests: %s', json.dumps(grouped_tests, indent=4))

    # Send grouped tests to SQS queue
    for test_number, test_step in grouped_tests.items():
        message_body = json.dumps(test_step)
        sqs_client.send_message(QueueUrl=QUEUE_URL, MessageBody=message_body)
        logger.info(f'Sent message for test_case {test_number} to SQS queue')

    return {
        'statusCode': 200,
        'Message': 'Processing complete'
    }
