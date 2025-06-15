import os
from typing import Optional, Mapping

from aws_cdk.aws_logs import RetentionDays
from aws_cdk.aws_iam import Role
from aws_cdk import aws_lambda as _lambda
from aws_cdk.aws_logs import LogGroup
from aws_cdk import RemovalPolicy, Duration
from constructs import Construct


def create_lambda(
    self: Construct,
    id: str,
    role: Role,
    function_name: Optional[str],
    description: Optional[str],
    environment: Optional[Mapping[str, str]],
    timeout: Optional[Duration] = None,
    inline: bool = True,
) -> _lambda.Function:
    """
    Create a Lambda function and log group with default settings

    Parameters:
        inline: Makes it easier to dploy single-file lambdas without staging assest in S3 first.

    Returns:
        _lambda.Function: The created Lambda function

    """

    state = self.node.try_get_context('stage') or 'dev'

    # Set LOGGING_LEVEL based on the stage
    logging_level = 'ERROR' if state == 'prod' else 'DEBUG'

    # Merge LOGGING_LEVEL into environment
    environment = {
        'LOGGING_LEVEL': logging_level,
        **(environment or {}),
    }

    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up two directory levels to get to the project root (lex-analytics)
    project_root = os.path.dirname(os.path.dirname(script_dir))
    lambda_path = os.path.join(project_root, 'lambdas', id, 'index.py')

    if inline:
        index_file_path = os.path.join(project_root, 'lambdas', id, 'index.py')
        with open(index_file_path, 'r', encoding='utf-8') as file:
            code = _lambda.Code.from_inline(file.read())
    else:
        code = _lambda.Code.from_asset(lambda_path)

    fn = _lambda.Function(
        self,
        id=f'{id}Lambda',
        role=role,
        function_name=function_name,
        description=description,
        runtime=_lambda.Runtime.PYTHON_3_9,
        architecture=_lambda.Architecture.ARM_64,
        handler='index.handler',
        environment=environment,
        timeout=timeout,
        code=code,
    )

    # TODO: What are our prod retention rules?
    retention = (
        RetentionDays.ONE_MONTH if state == 'prod' else RetentionDays.ONE_WEEK
    )

    LogGroup(
        self,
        id=f'{id}LogGroup',
        log_group_name=f'/aws/lambda/{fn.function_name}',
        retention=retention,
        removal_policy=RemovalPolicy.DESTROY,
    )

    return fn