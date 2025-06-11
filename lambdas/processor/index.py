import os
import logging
import boto3
import datetime
import uuid
import json
import time

QUEUE_URL = os.environ.get('QUEUE_URL')
FIREHOSE_NAME = os.environ.get('FIREHOSE_NAME')

logging.basicConfig(level=os.environ.get('LOGGING_LEVEL', 'DEBUG'))
logger = logging.getLogger(__name__) # __name__ is the name of the module

sqs_client = boto3.client('sqs')
firehose_client = boto3.client('firehose')
lex_client = boto3.client('lex-runtime')

# set a unique identifier for this test run (stored as Lex session attribute)
test_run_id = datetime.datetime.now().strftime('%Y%m%d%H%M%S')

# set request attribute for Lex test runs (stored as Lex request attribute)
channel_attribute = 'lex lambda test analytics'

def flush_logs():
    """Flush all logging handlers to ensure all logs are sent to CloudWatch before sending to Lex.
    This is the process of ensuring that all buffered log data is written to the log file or storage medium immediately. This is important to prevent data loss, especially in cases of unexpected system crashes or shutdowns
    """
    for handler in logger.handlers:
        handler.flush()


def execute_test_case(test_case: list[dict]) -> list[dict]:
    """Execute a test case and return the results"""
    attributes = ''
    session_id = None
    request_attributes = {'channel': channel_attribute}

    # loop through each step in the test case
    # step = row
    for step in test_case:
        logger.debug(f'Evaluating Test={step["Test Case"]}, Step={step["Step"]}')

        # if the step is a number, it is a test stepsession_attributes
        if int(step['Step']) == 1:
            # create a new session
            session_id = str(uuid.uuid4())
            logger.debug('             new session: {}'.format(session_id))

            # reset the session attributes form the test case
            attributes: str = step['Session Attributes']

            # parse the session attributes
            if len(attributes) > 0:
                attributes = attributes.rstrip(',') # remove trailing comma
                session_attributes = dict(item.split('=') for item in attributes.split(','))
            else:
                session_attributes = {}

        # increase Lex's timeout limit for the Lambda codehook
        session_attributes['x-amz-lex:codehook-timeout-ms'] = '90000'

        session_attributes['test-run'] = '{}'.format(test_run_id) # test run identifier
        session_attributes['test-case'] = '{:0>3}'.format(step['Test Case']) # :0>3 means 3 digits, padded with zeros
        session_attributes['test-step'] = '{:0>3}'.format(step['Step']) # :0>3 means 3 digits, padded with zeros
        session_attributes['expected-response'] = '{}'.format(step['Expected Response']) # expected response
        session_attributes['expected-intent'] = step['Expected Intent'] # expected intent

        logger.debug('session attributes: {}'.format(json.dumps(session_attributes)))

        session_state = {'sessionAttributes': session_attributes}
        user_input = step['User Input']

        logger.info(f'Session: {session_id}: calling Lex for test step [{step["Test Case"]}, {step["Step"]}]')

        # call Lex
        bot_response = None
        try:
            # call Lex
            bot_response = lex_client.recognize_text(
                botId=step['BotId'],
                botAliasId=step['AliasId'],
                localeId=step['LocaleId'],
                sessionId=session_id,
                text=user_input,
                sessionState=session_state,
                requestAttributes=request_attributes
            )
            logger.error(f'Bot Response = {json.dumps(bot_response, indent=2)}')
        except Exception as e:
            step['Error'] = str(e)
            logger.error('Exception calling lex for test step [{},{}]. Error = {}'.format(step['Test Case'], step['Step'], str(e)))
            logger.error(f'Record = {json.dumps(step)}')

            break

        # check if we got a response from Lex
        if bot_response == None:
            logger.error('No reponse from Lex for test step [{},{}]'.format(step['Test Case'], step['Step']))
            break

        logger.info("--called Lex for test step [{},{}]".format(step['Test Case'], step['Step']))

        logger.info(json.dumps(bot_response, indent=4))

        step['Response'] = bot_response.get('message', [{}])[0].get('content', '[no Response>')
        step['Actual Intent'] = bot_response['sessionState']['intent']['name']
        step['Actual State'] = bot_response['sessionState']['intent']['state']

        result_attributes = bot_response['sessionState']['sessionAttributes']
        step['Test Result'] = result_attributes.get('test-result', '')
        step['Test Explanation'] = result_attributes.get('test-explanation', '')

        logger.debug(f'Session: {session_id}: Answer test step: [{step["Test Case"]}.{step["Step"]} is {step["Response"]}')

    return test_case

# process a list of test cases
def process_test_cases(test_cases: list[list[dict]]):
    test_results: list[list[dict]] = []
    start_time = time.perf_counter()
    for test_case in test_cases:
        test_results.append(execute_test_case(test_case))
    duration = time.perf_counter() - start_time
    return duration, test_results

# main handler
def handler(event, context):
    print('Received event: %s', json.dumps(event))

    # Parse SQS message
    test_cases = [json.loads(record['body']) for record in event['Records']]
    logger.info('Received %d test cases', len(test_cases))

    # Process test cases
    duration, test_results = process_test_cases(test_cases)
    logger.info(f'Duration = {duration:.0f} seconds')

    # Remove processed messages from SQS
    for record in event['Records']:
        sqs_client.delete_message(QUEUE_URL, ReceiptHandle=record['receiptHandle'])

    logger.info('Processing complete')
    flush_logs()
    return test_results
