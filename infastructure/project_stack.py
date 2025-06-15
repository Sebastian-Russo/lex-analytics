from aws_cdk import (
    Duration,
    Stack,
    aws_sqs as sqs,
    aws_s3 as s3,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_kinesisfirehose as firehose,
    aws_events as events,
    aws_events_targets as targets,
    aws_glue as glue,
    Aws as cdk_aws,
)
from aws_cdk import RemovalPolicy
from constructs import Construct
from infastructure.config import AppConfig
from infastructure.util.create_lambda import create_lambda

class LexTestTool(Stack):

    def __init__(self, scope: Construct, construct_id: str, props: AppConfig, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.props = props
        is_prod = (self.node.try_get_context('stage') or 'dev') == 'prod'

        # lambda_role = iam.Role.from_role_name(self, "LambdaRole", props.lambda_role_name)
        lambda_role = iam.Role(
            self,
            "LambdaRole",
            role_name=f"{props.prefix}-lambda-role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
        )

        # Define the SQS queue
        test_queue = sqs.Queue(self, "TestQueue", queue_name=f"{props.prefix}-test-queue", visibility_timeout=Duration.seconds(30),
        )

        initializer = create_lambda(
            self,
            'initializer',
            lambda_role,
            function_name=f"{props.prefix}-initializer",
            description="Read test cases from S3 and queues them up in SQS. Triggered by S3 file drop.",
            environment={
                "QUEUE_URL": test_queue.queue_url,
            },
        )

        # results_bucket = s3.Bucket.from_bucket_name(self, "ResultsBucket", props.results_bucket_name)
        # Create a new bucket instead of using an existing one
        results_bucket = s3.Bucket(
            self,
            "ResultsBucket",
            bucket_name=f"{props.prefix}-results-bucket",
            removal_policy=RemovalPolicy.DESTROY, # TODO: change when in real use
            auto_delete_objects=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            versioned=True,
        )


        event_rule = events.Rule(
            self,
            "S3UploadRule",
            rule_name=f"{props.prefix}-s3-upload-rule",
            event_pattern=events.EventPattern(
                source=["aws.s3"],
                detail_type=["Object Created"],
                detail={
                    "bucket": {
                        "name": [results_bucket.bucket_name]
                    },
                    "object": {
                        "key": [{"prefix": f'{props.prefix}/input/'}]
                    }
                }
            ),
        )

        event_rule.add_target(targets.LambdaFunction(initializer))

        # firehose_role = iam.Role.from_role_arn(self, "FirehoseRole", props.firehose_role_arn)
        firehose_role = iam.Role(
            self,
            "FirehoseRole",
            role_name=f"{props.prefix}-firehose-role",
            assumed_by=iam.ServicePrincipal("firehose.amazonaws.com"),
        )

        # Create a firehose delivery stream that sends data to S3
        results_firehose = firehose.CfnDeliveryStream(self, "ResultsFirehose",
            delivery_stream_name=f"{props.prefix}-results",
            s3_destination_configuration={
                "bucketArn": results_bucket.bucket_arn,
                "roleArn": firehose_role.role_arn,
                "prefix": f"{props.prefix}/results/",
                "errorOutputPrefix": f"{props.prefix}/error/",
                "bufferingHints": {
                    "sizeInMBs": 25, # Buffer size
                    "intervalInSeconds": 300 if is_prod else 15,
                },
            }
        )


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
            database_name=f"{props.prefix}-glue",
            catalog_id=cdk_aws.ACCOUNT_ID,
            database_input={
                'name': props.prefix
            }
        )

        glue_table = glue.CfnTable(
            self,
            "ResultsTable",
            catalog_id=cdk_aws.ACCOUNT_ID,
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