#!/usr/bin/env python3

import aws_cdk as cdk
from .config import get_config
from .project_stack import LexTestTool
from .util.get_project_meta import get_project_meta

app = cdk.App()

# Get deployment state from context, default to 'dev' if not specified
stage = app.node.try_get_context('stage') or 'dev'
configs = get_config(stage)

# Create the stack
for cfg in configs:
    id = 'East'
    if cfg.region == 'us-west-2':
        id = 'West'
    LexTestTool(app, id, cfg)

# Add global tags
meta = get_project_meta()
cdk.Tags.of(app).add_all('Prefix',meta.name) # tag all resources with project name
cdk.Tags.of(app).add_all('Version', meta.version) # tag all resources with project version

app.synth()
