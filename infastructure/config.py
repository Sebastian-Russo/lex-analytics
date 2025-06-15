"""
Contains environment specific configurations based on deployment stage.
"""

# TODO: InstanceId should be the same for ACGR environments. Maybe we make region an array instead?
#    Pros: App config looks much cleaner
#    Cons: Not all reources will have same ids. Example: if we depend on cognito user pool, that will be different for each region. Alterantively, we look up the pool from parameter store.

from dataclasses import dataclass

from infastructure.util.get_project_meta import get_project_meta

meta = get_project_meta()

@dataclass
class AppConfig:
    """Base configuration class wiht common settings for the environment. Implemented as a class to enfore type checking and provide a clear structure."""

    account: str
    region: str
    # lambda_role_name: str
    # firehose_role_arn: str
    # results_bucket_name: str

    prefix: str = meta.name



# Configuration mapping
CONFIGS = {
    'dev': [
        AppConfig(
            account='308665918648',
            region='us-east-1',
            # lambda_role_name='TODO',
            # firehose_role_arn='TODO',
            # results_bucket_name='TODO'
        ),
    ],
    'val': [
        AppConfig(
            account='TODO',
            region='TODO',
            # lambda_role_name='TODO',
            # firehose_role_arn='TODO',
            # results_bucket_name='TODO'
        ),
    ],
    'prod': [
        AppConfig(
            account='TODO',
            region='TODO',
            # lambda_role_name='TODO',
            # firehose_role_arn='TODO',
            # results_bucket_name='TODO'
        ),
    ],
}

def get_config(stage):
    """Get the configuration for the specified stage.

    Args:
    stage (str): The deployment stage (dev, staging, prod)

    Returns:
    list[AppConfig]: The configuration for the specified stage. Prod will have two configs.

    Raises:
    ValueError: If the specified stage is not supported
    """
    if stage not in CONFIGS:
        raise ValueError(f"Unsupported stage: '{stage}'", "Valid options are: {','.join(CONFIGS.keys())}")

    config = CONFIGS[stage]
    for c in config:
        print(f'Configuration for stage {stage}:\n{c.__dict__}\n')

    return config
