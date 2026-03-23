#!/usr/bin/env python3
import os
import aws_cdk as cdk

from failure_propagation_infra.stack import FailurePropagationStack

app = cdk.App()

FailurePropagationStack(
    app,
    "FailurePropagationAnalyzerStack",
    # Region/account are taken from your AWS CLI env/profile at deploy time.
    env=cdk.Environment(
        account=os.getenv("CDK_DEFAULT_ACCOUNT"),
        region=os.getenv("CDK_DEFAULT_REGION"),
    ),
)

app.synth()