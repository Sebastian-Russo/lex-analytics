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
    """Execute a test_case and return the results"""
    attributes = ''
    session_id = None
    request_attributes = {'channel': channel_attribute}
    session_attributes = {
        # increase Lex's timeout limit for the Lambda codehook
        'x-amz-lex:codehook-timeout-ms': '90000',
    }
    session_state = {'sessionAttributes': session_attributes}

    # loop through each step in the test_case
    # step = row
    for step in test_case:
        logger.debug(f'Evaluating Test={step["test_case"]}, Step={step["Step"]}')

        # if the step is a number, it is a test stepsession_attributes
        if int(step['step']) == 1:
            # create a new session
            session_id = str(uuid.uuid4())
            logger.debug('new session: {}'.format(session_id))

            # reset the session attributes form the test_case
            attributes: str = step['session_attributes']

            # parse the session attributes
            if len(attributes) > 0:
                attributes = attributes.rstrip(',') # remove trailing comma
                dict(item.split('=') for item in attributes.split(','))



        session_attributes['test-run'] = '{}'.format(test_run_id) # test run identifier
        session_attributes['test-case'] = '{:0>3}'.format(step['test_case']) # :0>3 means 3 digits, padded with zeros
        session_attributes['test-step'] = '{:0>3}'.format(step['step']) # :0>3 means 3 digits, padded with zeros
        session_attributes['expected-response'] = '{}'.format(step['expected_response']) # expected response
        session_attributes['expected-intent'] = step['expected_intent'] # expected intent

        logger.debug('session attributes: {}'.format(json.dumps(session_attributes)))

        session_state = {'sessionAttributes': session_attributes}
        user_input = step['utterance']

        logger.info(f'Session: {session_id}: calling Lex for test step [{step["test_case"]}, {step["step"]}]')

        # call Lex
        bot_response = None
        try:
            # call Lex
            bot_response = lex_client.recognize_text(
                botId=step['bot_id'],
                botAliasId=step['alias_id'],
                localeId=step['locale_id'],
                sessionId=session_id,
                text=user_input,
                sessionState=session_state,
                requestAttributes=request_attributes
            )
            logger.error(f'Bot Response = {json.dumps(bot_response, indent=2)}')
        except Exception as e:
            step['Error'] = str(e)
            logger.error('Exception calling lex for test step [{},{}]. Error = {}'.format(step['test_case'], step['Step'], str(e)))
            logger.error(f'Record = {json.dumps(step)}')

            break

        # check if we got a response from Lex
        if bot_response == None:
            logger.error('No reponse from Lex for test step [{},{}]'.format(step['test_case'], step['Step']))
            break

        logger.info("--called Lex for test step [{},{}]".format(step['test_case'], step['Step']))

        logger.info(json.dumps(bot_response, indent=4))

        step['response'] = bot_response.get('message', [{}])[0].get('content', '[no Response>')

        # Update our local state variables
        session_state = bot_response.get('sessionState', {})
        session_attributes = session_state.get('sessionAttributes', {})

        step['actual_intent'] = session_attributes.get('actual_intent', '')
        step['actual_state'] = session_attributes.get('actual_state', '')
        step['test_result'] = session_attributes.get('test_result', '')
        step['test_explanation'] = session_attributes.get('test_explanation', '')


        logger.debug(f'Session: {session_id}: Answer test step: [{step["test_case"]}.{step["Step"]} is {step["Response"]}')

    return test_case

# process a list of test_cases
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
    logger.info('Received %d test_cases', len(test_cases))

    # Process test_cases
    duration, test_results = process_test_cases(test_cases)
    logger.info(f'Duration = {duration:.0f} seconds')

    # Remove processed messages from SQS
    for record in event['Records']:
        sqs_client.delete_message(QUEUE_URL, ReceiptHandle=record['receiptHandle'])

    logger.info('Processing complete')
    flush_logs()
    return test_results
