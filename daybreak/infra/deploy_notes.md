# Infrastructure & AWS Deployment Notes

## Overview
MyAlexa supports zero-AWS local development using `STORAGE=memory` by default. When connecting to AWS infrastructure, it utilizes:
1. **Amazon DynamoDB**: Single-table key-value & document store for persistent events, tasks, and daily plans.
2. **Amazon Bedrock**: Foundation model inference (Nova / Claude) for natural spoken schedule summaries.
3. **Bedrock AgentCore**: Production container runtime for hosting Strands Agents.

## 1. DynamoDB Table Provisioning
The table `planner` is structured with composite primary keys (`pk`, `sk`) to support single-table design patterns.

### Option A: Python Script (boto3)
```bash
python daybreak/infra/create_dynamodb_table.py
```

### Option B: AWS CLI
```bash
aws dynamodb create-table \
  --table-name planner \
  --attribute-definitions AttributeName=pk,AttributeType=S AttributeName=sk,AttributeType=S \
  --key-schema AttributeName=pk,KeyType=HASH AttributeName=sk,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

## 2. IAM Configuration
Attach [`iam_policy.json`](file:///c:/Users/HP/AWS/daybreak/infra/iam_policy.json) to your IAM role/user executing the server or Strands agent.

## 3. Switching Backend
Update `.env`:
```env
STORAGE=dynamodb
DYNAMODB_TABLE_NAME=planner
AWS_REGION=us-east-1
```
