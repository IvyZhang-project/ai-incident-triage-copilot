# Deployment Notes

The repository includes a production-shaped container path while keeping real
AWS deployment optional for the portfolio MVP.

## Local Container

From the repository root:

```bash
docker build -t ai-incident-triage-copilot .
docker run --rm -p 8000:8000 \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -e OPENAI_MODEL="gpt-4.1-mini" \
  ai-incident-triage-copilot
```

Use `/health` as the container health-check path and port `8000` as the service
port.

## Recommended MVP Deployment: AWS App Runner

1. Build the image and push it to Amazon ECR.
2. Create an App Runner service from the ECR image.
3. Configure port `8000` and health path `/health`.
4. Store the OpenAI key in AWS Secrets Manager or Systems Manager Parameter
   Store; inject it as `OPENAI_API_KEY` rather than placing it in the image.
5. Send application logs to CloudWatch and add alarms for HTTP 5xx responses,
   latency, and unhealthy instances.
6. Apply least-privilege IAM permissions to the App Runner instance role.

App Runner is suitable for this MVP because it deploys a stateless HTTP
container with less operational work than managing an ECS cluster.

## ECS Fargate Alternative

ECS Fargate provides more control over networking, task sizing, autoscaling,
load balancers, IAM roles, and deployment strategies. Use it when the project
needs VPC-only data sources, private CloudWatch access paths, or more explicit
operational configuration.

Suggested components:

- ECR repository
- ECS cluster and Fargate task definition
- Application Load Balancer with `/health` checks
- Secrets Manager reference for `OPENAI_API_KEY`
- CloudWatch log group and alarms
- IAM task execution and task roles

## Current Storage Constraint

Trace records are held in an in-memory dictionary. App Runner or ECS may run
multiple instances and replace containers at any time, so traces are not durable
or shared. A production extension should store traces in DynamoDB, PostgreSQL,
or an observability platform and apply retention and sensitive-data policies.

## Future CloudWatch Integration

`CloudWatchLikeIncidentLoader` already models the query boundary: service,
region, and time window are converted into an `IncidentBundle`. A real adapter
can implement the same interface using CloudWatch Logs Insights and metric APIs.

Production requirements would include:

- Explicit log groups, metric namespaces, accounts, and regions
- Query timeouts, pagination, retries, and rate-limit handling
- Least-privilege IAM permissions
- Tenant and incident access controls
- Query cost and scanned-data monitoring
- Redaction of credentials, tokens, and personal data

Real AWS calls are intentionally outside the six-week MVP because the core
portfolio value is the loader boundary, deterministic filtering, retrieval,
validation, fallback, traceability, and evaluation design.
