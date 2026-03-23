from __future__ import annotations

from dataclasses import dataclass

from aws_cdk import (
    Stack,
    CfnOutput,
    Duration,
    aws_dynamodb as dynamodb,
    aws_lambda as _lambda,
    aws_sns as sns,
    aws_sns_subscriptions as subs,
    aws_events as events,
    aws_events_targets as targets,
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

        project_name = self.node.try_get_context("projectName") or "failure-propagation-analyzer"
        schedule_minutes = int(self.node.try_get_context("scheduleMinutes") or 5)

        use_existing = bool(self.node.try_get_context("useExistingResources") or False)
        existing_cfg = None
        if use_existing:
            existing_cfg = ExistingResourcesConfig(
                sns_topic_arn=str(self.node.try_get_context("existingSnsTopicArn") or "").strip(),
                state_table_name=str(self.node.try_get_context("existingStateTableName") or "service_state").strip(),
                graph_table_name=str(self.node.try_get_context("existingGraphTableName") or "service_dependency_graph").strip(),
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
                self, "StateTable", table_name=existing_cfg.state_table_name
            )
            graph_table = dynamodb.Table.from_table_name(
                self, "GraphTable", table_name=existing_cfg.graph_table_name
            )
            state_table_name = existing_cfg.state_table_name
            graph_table_name = existing_cfg.graph_table_name
        else:
            # CHANGED: use unique table names so we don't collide with existing tables
            state_table = dynamodb.Table(
                self,
                "ServiceStateTable",
                table_name="service_state_cdk",
                partition_key=dynamodb.Attribute(
                    name="service_name", type=dynamodb.AttributeType.STRING
                ),
                billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
                point_in_time_recovery=True,
            )

            graph_table = dynamodb.Table(
                self,
                "ServiceDependencyGraphTable",
                table_name="service_dependency_graph_cdk",
                partition_key=dynamodb.Attribute(
                    name="service_name", type=dynamodb.AttributeType.STRING
                ),
                billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
                point_in_time_recovery=True,
            )
            state_table_name = state_table.table_name
            graph_table_name = graph_table.table_name

        # -----------------------------
        # SNS
        # -----------------------------
        if use_existing and existing_cfg:
            topic = sns.Topic.from_topic_arn(self, "AlertsTopic", existing_cfg.sns_topic_arn)
        else:
            topic = sns.Topic(
                self,
                "FailurePropagationAlertsTopic",
                topic_name="failure-propagation-alerts-cdk",
                display_name="Failure Propagation Alerts",
            )

            # Email subscription (requires user to confirm via email)
            alert_email = (self.node.try_get_context("alertEmail") or "").strip()
            if alert_email:
                topic.add_subscription(subs.EmailSubscription(alert_email))

        # -----------------------------
        # Lambda (your handler)
        # -----------------------------
        fn = _lambda.Function(
            self,
            "FailurePropagationLambda",
            function_name=f"{project_name}-lambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="lambdas.failure_propagation.handler.lambda_handler",
            code=_lambda.Code.from_asset(
                "..",
                exclude=[
                    "infra/cdk.out/**",
                    "infra/.venv/**",
                    ".venv/**",
                    "**/__pycache__/**",
                    "**/.pytest_cache/**",
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

        # Permissions
        state_table.grant_read_write_data(fn)
        graph_table.grant_read_data(fn)
        topic.grant_publish(fn)

        # -----------------------------
        # EventBridge scheduled trigger
        # -----------------------------
        rule = events.Rule(
            self,
            "ScheduledAnalysisRule",
            rule_name=f"{project_name}-scheduled-analysis",
            schedule=events.Schedule.rate(Duration.minutes(schedule_minutes)),
        )
        rule.add_target(
            targets.LambdaFunction(
                fn,
                event=events.RuleTargetInput.from_object({"run_mode": "scheduled"}),
            )
        )

        # -----------------------------
        # Outputs (nice for README/demo)
        # -----------------------------
        CfnOutput(self, "StateTableName", value=state_table_name)
        CfnOutput(self, "GraphTableName", value=graph_table_name)
        CfnOutput(self, "AlertsTopicArn", value=topic.topic_arn)
        CfnOutput(self, "LambdaFunctionName", value=fn.function_name)
        CfnOutput(self, "ScheduleMinutes", value=str(schedule_minutes))
