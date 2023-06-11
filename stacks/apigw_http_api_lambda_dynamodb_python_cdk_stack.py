# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import os
from aws_cdk import (
    CfnParameter,
    Stack,
    aws_dynamodb as dynamodb_,
    aws_lambda as lambda_,
    aws_apigateway as apigw_,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_secretsmanager as secretmanager,
    Duration,
)
from datadog_cdk_constructs_v2 import Datadog
from constructs import Construct

TABLE_NAME = "registration_table"
WEB_URL = "https://dev.d3q9h9cgsw72b7.amplifyapp.com"





class ApigwHttpApiLambdaDynamodbPythonCdkStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        secret_arn = CfnParameter(self, "secretARN", type="String",
            description="The kms key ARN used to enrypt the Datadog API Key.")

        secret_dd_api = secretmanager.Secret.from_secret_partial_arn(
            self, 
            'DdApiKeySecret-2JoN3bz178J2',
            secret_arn.value_as_string
            )
        datadog = Datadog(self, "Datadog",
            python_layer_version=72,
            extension_layer_version=43,
            site="datadoghq.eu",
            api_key_secret=secret_dd_api,
            env="prod",
            service="lambda-users",
            version="1.0",
            tags="app:mydummyapp,function:register",
        )

        # VPC
        vpc = ec2.Vpc(
            self,
            "Ingress",
            ip_addresses=ec2.IpAddresses.cidr("10.1.0.0/16"),
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Poublic-Subnet", subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="Private-Subnet", subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24
                )
            ],
        )
        
        # Create VPC endpoint
        dynamo_db_endpoint = ec2.GatewayVpcEndpoint(
            self,
            "DynamoDBVpce",
            service=ec2.GatewayVpcEndpointAwsService.DYNAMODB,
            vpc=vpc,
        )

        # This allows to customize the endpoint policy
        dynamo_db_endpoint.add_to_policy(
            iam.PolicyStatement(  # Restrict to listing and describing tables
                principals=[iam.AnyPrincipal()],
                actions=[                "dynamodb:DescribeStream",
                "dynamodb:DescribeTable",
                "dynamodb:Get*",
                "dynamodb:Query",
                "dynamodb:Scan",
                "dynamodb:CreateTable",
                "dynamodb:Delete*",
                "dynamodb:Update*",
                "dynamodb:PutItem"],
                resources=["*"],
            )
        )

        # Create DynamoDb Table
        demo_table = dynamodb_.Table(
            self,
            TABLE_NAME,
            partition_key=dynamodb_.Attribute(
                name="id", type=dynamodb_.AttributeType.STRING
            ),
        )

        # Create the Lambda function to receive the request
        api_hanlder = lambda_.Function(
            self,
            "UsersApiHandler",
            function_name="register_handler",
            runtime=lambda_.Runtime.PYTHON_3_9,
            code=lambda_.Code.from_asset("lambda/apigw-handler"),
            handler="index.handler",
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            memory_size=1024,
            timeout=Duration.seconds(1),
        )
        datadog.add_lambda_functions([api_hanlder])


        # grant permission to lambda to write to demo table
        demo_table.grant_write_data(api_hanlder)
        api_hanlder.add_environment("TABLE_NAME", demo_table.table_name)
        api_hanlder.add_environment("WEB_URL", WEB_URL)

        # Create API Gateway
        api = apigw_.LambdaRestApi(
            self,
            "users",
            handler=api_hanlder,
            default_cors_preflight_options=apigw_.CorsOptions(
                allow_origins=apigw_.Cors.ALL_ORIGINS,
                allow_headers=['Content-Type','X-Amz-Date','Authorization','X-Api-Key','X-Amz-Security-Token','x-datadog-origin','x-datadog-parent-id','x-datadog-trace-id','x-datadog-sampling-priority']
            )
        )
        users = api.root.add_resource("register")
        users.add_method("POST") # POST /users