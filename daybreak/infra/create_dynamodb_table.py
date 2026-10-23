"""
Script to create the DynamoDB single-table 'planner' for MyAlexa.
Uses PAY_PER_REQUEST billing mode with pk (HASH) and sk (RANGE).
"""
import os
import sys
import boto3
from botocore.exceptions import ClientError


def create_planner_table():
    table_name = os.getenv("DYNAMODB_TABLE_NAME", "planner")
    region = os.getenv("AWS_REGION", "us-east-1")
    
    print(f"Connecting to DynamoDB in region {region}...")
    dynamodb = boto3.resource("dynamodb", region_name=region)
    
    try:
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {"AttributeName": "pk", "KeyType": "HASH"},
                {"AttributeName": "sk", "KeyType": "RANGE"}
            ],
            AttributeDefinitions=[
                {"AttributeName": "pk", "AttributeType": "S"},
                {"AttributeName": "sk", "AttributeType": "S"}
            ],
            BillingMode="PAY_PER_REQUEST"
        )
        print(f"Creating table '{table_name}'... Please wait.")
        table.wait_until_exists()
        print(f"Table '{table_name}' created successfully!")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceInUseException":
            print(f"Table '{table_name}' already exists.")
        else:
            print(f"Error creating table: {e}")
            sys.exit(1)


if __name__ == "__main__":
    create_planner_table()
