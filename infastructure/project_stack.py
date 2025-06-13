from aws_cdk import (
    Duration,
    Stack,
    aws_sqs as sqs,
    aws_s3 as s3,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_kinesisfirehose as firehose,
)
from constructs import Construct
from app_config import AppConfig
from util.create_lambda import create_lambda

class ProjectStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, props: AppConfig, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.props = props
        is_prod = (self.node.try_get_context('stage') or 'dev') == 'prod'

        lambda_role = iam.Role.from_role_name(self, "LambdaRole", props.lambda_role_name)

        # Define the SQS queue
        test_queue = sqs.Queue(self, "TestQueue", queue_name=f"{props.prefix}-test-queue", visibility_timeout=Duration.seconds(30),
        )

        create_lambda(
            self,
            'initializer',
            lambda_role,
            function_name=f"{props.prefix}-initializer",
            description="Read test cases from S3 and queues them up in SQS. Triggered by S3 file drop.",
            environment={
                "QUEUE_URL": test_queue.queue_url,
            },
        )

        results_bucket = s3.Bucket.from_bucket_name(self, "ResultsBucket", props.results_bucket_name)
        firehose_role = iam.Role.from_role_arn(self, "FirehoseRole", props.firehose_role_arn)

        results_firehose = firehose.CfnDeliveryStream(self, "ResultsFirehose", delivery_stream_name=f"{props.prefix}-results", s3_destination_configuration={
            "bucket_arn": results_bucket.bucket_arn,
            "role_arn": firehose_role.role_arn,
            "prefix": f"{props.prefix}/results/",
            "error_output_prefix": f"{props.prefix}/error/",
            "buffering_hints": {
                "size_in_mb": 25, # Buffer size
                "interval_in_seconds": 300 if is_prod else 15, #
            },
        })


        processor = create_lambda(
            self,
            'processor',
            lambda_role,
            function_name=f"{props.prefix}-processor",
            timeout=Duration.seconds(10),
            description="Process test cases from SQS and send results to Firehose.",
            environment={
                "FIREHOSE_NAME": results_firehose.delivery_stream_name,
            },
        )

        # Manually create the event source mapping
        lambda_.CfnEventSourceMapping(
            self,
            "ProcessorEventSourceMapping",
            function_name=processor.function_name,
            event_source_arn=test_queue.queue_arn,
            batch_size=10
        )

        glue_database = glue.CfnDatabase(
            self,
            "Database",
            database_name=f"{props.prefix}-glue"
            catalog_id=cdk.Aws.ACCOUNT_ID,
            database_input={
                'name': props.prefix
            }
        )

        glue_table = glue.CfnTable(
            self,
            "ResultsTable"
            catalog_id=cdk.Aws.ACCOUNT_ID,
            database_name=glue_database.database_name,
            table_input={
                'name': 'results',
                'storage_descriptor': {
                    'columns': [
                        {'name': 'test_run', 'type': 'string'},
                        {'name': 'test_case', 'type': 'string'},
                        {'name': 'step', 'type': 'string'},
                        {'name': 'utterance', 'type': 'string'},
                        {'name': 'session_attributes', 'type': 'string'},
                        {'name': 'expected_response', 'type': 'string'},
                        {'name': 'expected_intent', 'type': 'string'},
                        {'name': 'expected_state', 'type': 'string'},
                        {'name': 'bot_id', 'type': 'string'},
                        {'name': 'alias_id', 'type': 'string'},
                        {'name': 'locale_id', 'type': 'string'},
                        {'name': 'response', 'type': 'string'},
                        {'name': 'actual_intent', 'type': 'string'},
                        {'name': 'actual_state', 'type': 'string'},
                        {'name': 'test_result', 'type': 'string'},
                        {'name': 'test_explanation', 'type': 'string'},
                    ],
                    'location': f"s3://{results_bucket.bucket_name}/{props.prefix}/results",
                    'input_format': 'org.apache.hadoop.mapred.TextInputFormat',
                    'output_format': 'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat',
                    'serde_info': {
                        'serde_class_name': 'org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe',
                        'parameters': {
                            'serialization.format': '1'
                        }
                    }
                },
                'table_type': 'EXTERNAL_TABLE',
            }
        )