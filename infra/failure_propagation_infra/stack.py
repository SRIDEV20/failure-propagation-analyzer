from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from aws_cdk import (
    Stack,
    CfnOutput,
    Duration,
    BundlingOptions,
    aws_dynamodb as dynamodb,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_sns as sns,
    aws_sns_subscriptions as subs,
    aws_events as events,
    aws_events_targets as targets,
    aws_apigateway as apigateway,
)
from constructs import Construct


@dataclass
class ExistingResourcesConfig:
    sns_topic_arn: str
    state_table_name: str
    graph_table_name: str


class FailurePropagationStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        project_name = (
            self.node.try_get_context("projectName")
            or "failure-propagation-analyzer"
        )

        schedule_minutes = int(
            self.node.try_get_context("scheduleMinutes") or 5
        )

        use_existing = bool(
            self.node.try_get_context("useExistingResources") or False
        )

        existing_cfg = None

        if use_existing:
            existing_cfg = ExistingResourcesConfig(
                sns_topic_arn=str(
                    self.node.try_get_context("existingSnsTopicArn") or ""
                ).strip(),
                state_table_name=str(
                    self.node.try_get_context("existingStateTableName")
                    or "service_state"
                ).strip(),
                graph_table_name=str(
                    self.node.try_get_context("existingGraphTableName")
                    or "service_dependency_graph"
                ).strip(),
            )

            if not existing_cfg.sns_topic_arn:
                raise ValueError(
                    "useExistingResources=true but existingSnsTopicArn is empty. "
                    "Set it via `cdk context` or in infra/cdk.json."
                )

        # -----------------------------
        # DynamoDB
        # -----------------------------
        if use_existing and existing_cfg:
            state_table = dynamodb.Table.from_table_name(
                self,
                "StateTable",
                table_name=existing_cfg.state_table_name,
            )

            graph_table = dynamodb.Table.from_table_name(
                self,
                "GraphTable",
                table_name=existing_cfg.graph_table_name,
            )

            state_table_name = existing_cfg.state_table_name
            graph_table_name = existing_cfg.graph_table_name

        else:
            state_table = dynamodb.Table(
                self,
                "ServiceStateTable",
                table_name="service_state_cdk",
                partition_key=dynamodb.Attribute(
                    name="service_name",
                    type=dynamodb.AttributeType.STRING,
                ),
                billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
                point_in_time_recovery_specification=(
                    dynamodb.PointInTimeRecoverySpecification(
                        enabled=True
                    )
                ),
            )

            graph_table = dynamodb.Table(
                self,
                "ServiceDependencyGraphTable",
                table_name="service_dependency_graph_cdk",
                partition_key=dynamodb.Attribute(
                    name="service_name",
                    type=dynamodb.AttributeType.STRING,
                ),
                billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
                point_in_time_recovery_specification=(
                    dynamodb.PointInTimeRecoverySpecification(
                        enabled=True
                    )
                ),
            )

            state_table_name = state_table.table_name
            graph_table_name = graph_table.table_name

        # -----------------------------
        # SNS
        # -----------------------------
        if use_existing and existing_cfg:
            topic = sns.Topic.from_topic_arn(
                self,
                "AlertsTopic",
                existing_cfg.sns_topic_arn,
            )

        else:
            topic = sns.Topic(
                self,
                "FailurePropagationAlertsTopic",
                topic_name="failure-propagation-alerts-cdk",
                display_name="Failure Propagation Alerts",
            )

            # Email subscription
            # Requires confirmation through email.
            alert_email = (
                self.node.try_get_context("alertEmail") or ""
            ).strip()

            if alert_email:
                topic.add_subscription(
                    subs.EmailSubscription(alert_email)
                )

        # -----------------------------
        # Analyzer Lambda
        # -----------------------------
        #
        # This is your EXISTING Lambda.
        # It is triggered by EventBridge.
        #
        lambda_package_dir = Path(__file__).resolve().parents[2] / "lambda_package"

        fn = _lambda.Function(
            self,
            "FailurePropagationLambda",
            function_name=f"{project_name}-lambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="lambdas.failure_propagation.handler.lambda_handler",
            code=_lambda.Code.from_asset(
                str(lambda_package_dir),
                exclude=[
                    "**/__pycache__/**",
                    "**/.pytest_cache/**",
                    "**/.venv/**",
                    "**/node_modules/**",
                    ".git/**",
                ],
            ),
            timeout=Duration.seconds(30),
            memory_size=256,
            environment={
                "STATE_TABLE_NAME": state_table_name,
                "GRAPH_TABLE_NAME": graph_table_name,
                "SNS_TOPIC_ARN": topic.topic_arn,
            },
        )

        # Analyzer Lambda permissions
        state_table.grant_read_write_data(fn)
        graph_table.grant_read_data(fn)
        topic.grant_publish(fn)

        # -----------------------------
        # FastAPI API Lambda
        # -----------------------------
        #
        # This is a SECOND Lambda.
        #
        # API Gateway
        #      ↓
        # FastAPI Lambda
        #      ↓
        # DynamoDB
        #
        api_fn = _lambda.Function(
            self,
            "FailurePropagationApiLambda",
            function_name=f"{project_name}-api",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="api.handler",
            code=_lambda.Code.from_asset(
                "..",
                exclude=[
                    "cdk.out/**",
                    "infra/cdk.out/**",
                    "infra/.venv/**",
                    ".venv/**",
                    "lambda_package/**",
                    "**/cdk.out/**",
                    "**/.venv/**",
                    "**/__pycache__/**",
                    "**/.pytest_cache/**",
                    ".git/**",
                    "frontend/node_modules/**",
                    "frontend/dist/**",
                ],
                bundling=BundlingOptions(
                    image=_lambda.Runtime.PYTHON_3_12.bundling_image,
                    command=[
                        "bash",
                        "-c",
                        (
                            "pip install -r /asset-input/requirements-api.txt "
                            "-t /asset-output && "
                            "cp /asset-input/api.py /asset-output/ && "
                            "cp -r /asset-input/engine /asset-output/"
                        ),
                    ],
                ),
            ),
            timeout=Duration.seconds(30),
            memory_size=512,
            environment={
                "STATE_TABLE_NAME": state_table_name,
                "GRAPH_TABLE_NAME": graph_table_name,
                "CORS_ALLOWED_ORIGINS": (
                    "http://localhost:5173,http://127.0.0.1:5173,"
                    "http://localhost:4173,http://127.0.0.1:4173,"
                    "https://failure-propagation-analyzer-five.vercel.app"
                ),
            },
        )

        # -----------------------------
        # API Lambda permissions
        # -----------------------------
        #
        # FastAPI only needs READ access
        # to the analyzer data.
        #
        state_table.grant_read_data(api_fn)
        graph_table.grant_read_data(api_fn)

        # -----------------------------
        # CloudWatch Logs permission
        # -----------------------------
        #
        # Required by the /logs endpoint
        # to retrieve Lambda log events.
        #
        api_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "logs:FilterLogEvents",
                ],
                resources=["*"],
            )
        )

        # -----------------------------
        # API Gateway
        # -----------------------------
        #
        # React
        #   ↓ HTTPS
        # API Gateway
        #   ↓
        # FastAPI Lambda
        #   ↓
        # DynamoDB
        #
        api = apigateway.LambdaRestApi(
            self,
            "FailurePropagationApi",
            handler=api_fn,
            proxy=True,
            endpoint_types=[
                apigateway.EndpointType.REGIONAL
            ],
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=apigateway.Cors.ALL_METHODS,
                allow_headers=[
                    "Content-Type",
                    "Authorization",
                ],
            ),
        )

        # -----------------------------
        # EventBridge scheduled trigger
        # -----------------------------
        #
        # Existing analyzer execution:
        #
        # EventBridge
        #      ↓
        # Analyzer Lambda
        #      ↓
        # DynamoDB
        #
        rule = events.Rule(
            self,
            "ScheduledAnalysisRule",
            rule_name=f"{project_name}-scheduled-analysis",
            schedule=events.Schedule.rate(
                Duration.minutes(schedule_minutes)
            ),
        )

        rule.add_target(
            targets.LambdaFunction(
                fn,
                event=events.RuleTargetInput.from_object(
                    {
                        "run_mode": "scheduled"
                    }
                ),
            )
        )

        # -----------------------------
        # Outputs
        # -----------------------------

        CfnOutput(
            self,
            "StateTableName",
            value=state_table_name,
        )

        CfnOutput(
            self,
            "GraphTableName",
            value=graph_table_name,
        )

        CfnOutput(
            self,
            "AlertsTopicArn",
            value=topic.topic_arn,
        )

        CfnOutput(
            self,
            "LambdaFunctionName",
            value=fn.function_name,
        )

        CfnOutput(
            self,
            "ScheduleMinutes",
            value=str(schedule_minutes),
        )

        CfnOutput(
            self,
            "ApiUrl",
            value=api.url,
            description="Failure Propagation Analyzer API URL",
        )