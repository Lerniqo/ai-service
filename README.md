# ai-service

FastAPI service with AWS SageMaker deployment via GitHub Actions CI/CD.

## Features
- ✅ Multi-environment configuration (development, testing, production)
- ✅ AWS SageMaker BYOC (Bring Your Own Container) ready
- ✅ GitHub Actions CI/CD pipeline
- ✅ SageMaker-compatible inference endpoints (`/ping`, `/invocations`)
- ✅ Kafka event consumer for real-time processing
- ✅ Automated deployment to AWS

## Tech Stack
- Python 3.11+
- FastAPI / Uvicorn
- Pydantic v2
- AWS SageMaker SDK
- Kafka (aiokafka)
- Docker

## Project Structure
```
.
├── app/
│   ├── __init__.py
│   ├── config.py              # Settings management & env loading
│   ├── main.py                # FastAPI application instance
│   ├── sagemaker/
│   │   ├── __init__.py
│   │   └── inference.py       # SageMaker inference handlers
│   ├── api/
│   │   └── health.py          # Health check endpoints
│   ├── clients/               # Service clients (Kafka, HTTP)
│   ├── consumers/             # Kafka event consumers
│   ├── core/                  # Core utilities (logging, exceptions)
│   └── schema/                # Pydantic schemas
├── serve                      # SageMaker inference entry point
├── train                      # SageMaker training entry point
├── run.py                     # Local development entrypoint
├── Dockerfile                 # Production SageMaker container
├── Dockerfile.sagemaker-lite  # Lightweight SageMaker container
├── nginx.conf                 # Nginx configuration for production
├── deploy_sagemaker.py        # Automated SageMaker deployment
├── scripts/
│   ├── build.sh               # Build Docker image
│   ├── test_local.sh          # Test container locally
│   ├── push_ecr.sh            # Push to Amazon ECR
│   └── cleanup.sh             # Clean up Docker resources
├── sample_events/             # Sample event payloads for testing
├── .env.development           # Env vars for development
├── .env.testing               # Env vars for testing
├── .env.production            # Env vars for production
├── requirements.txt           # Python dependencies
├── SAGEMAKER_DEPLOYMENT.md    # Detailed SageMaker deployment guide
└── README.md
```

## Prerequisites
- Python 3.11+ (recommended for SageMaker compatibility)
- pip
- Docker (for SageMaker deployment)
- AWS CLI (for SageMaker deployment)
- (Optional) A virtual environment tool: `venv`, `pyenv`, or `uv`

## Quick Start

### Local Development

```bash
# 1. Clone repository
git clone <repo-url>
cd ai-service

# 2. Create & activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.development .env.development.local  # (optional) override pattern

# 5. Start the service
make start-dev
# or
ENV=development python run.py
```

### SageMaker Deployment (BYOC)

```bash
# 1. Build the Docker container
./scripts/build.sh

# 2. Test locally
./scripts/test_local.sh

# 3. Deploy to AWS SageMaker
python deploy_sagemaker.py \
  --region us-east-1 \
  --role-arn arn:aws:iam::YOUR_ACCOUNT_ID:role/SageMakerExecutionRole
```

For detailed SageMaker deployment instructions, see [SAGEMAKER_DEPLOYMENT.md](SAGEMAKER_DEPLOYMENT.md).

## Environment Selection
The active environment is determined by the `ENV` variable (defaults to `development`). The loader reads `.env.<ENV>`.

Example: if `ENV=testing` then `.env.testing` is loaded before settings validation.

## Core Environment Variables
| Name | Description | Default (in code) | Typical Overrides |
|------|-------------|-------------------|-------------------|
| ENV | Current environment (`development`, `testing`, `production`) | development | Deployment target |
| APP_NAME | FastAPI title | MyApp | Branding |
| APP_VERSION | Application version | 1.0.0 | Release version |
| APP_DESCRIPTION | Docs description | This is my app | Documentation |
| HOST | Bind host | 127.0.0.1 | 0.0.0.0 in containers |
| PORT | Bind port | 8000 | 80 / 8080 in deployment |
| RELOAD | Enable autoreload (dev only) | False | True in `.env.development` |

Add new settings in `Settings` (in `app/config.py`) then expose via env file.

## Running (Make Targets)
```bash
make start-dev   # development (reload enabled if RELOAD=true in .env.development)
make start-test  # testing
make start-prod  # production
```

## Running (Manual)
```bash
ENV=development python run.py
ENV=testing python run.py
ENV=production python run.py
```

## Deployment Architecture

```
┌──────────────────┐
│  GitHub Repo     │
│  (main branch)   │
└────────┬─────────┘
         │ git push
         ▼
┌──────────────────┐
│ GitHub Actions   │
│ - Run tests      │
│ - Build Docker   │
│ - Push to ECR    │
│ - Deploy SageMaker│
└────────┬─────────┘
         │
         ▼
┌──────────────────┐     ┌──────────────────┐
│   Amazon ECR     │────→│  AWS SageMaker   │
│  (Docker Image)  │     │    Endpoint      │
└──────────────────┘     └──────────────────┘
```

### CI/CD Pipeline

Triggered on push to `main` or `production`:
1. ✅ Run tests
2. ✅ Build Docker image  
3. ✅ Push to Amazon ECR
4. ✅ Deploy to SageMaker
5. ✅ Endpoint ready (~5-10 min)

## SageMaker Endpoints

The deployed service exposes:

- **`/ping`** - Health check (GET)
- **`/invocations`** - Inference endpoint (POST)

## Using the Deployed Endpoint

```python
import boto3
import json

runtime = boto3.client('sagemaker-runtime', region_name='us-east-1')

response = runtime.invoke_endpoint(
    EndpointName='ai-service-endpoint',
    ContentType='application/json',
    Body=json.dumps({
        "eventType": "quiz_attempt",
        "userId": "user_123",
        "data": {
            "quiz_id": "quiz_456",
            "score": 85.5,
            "concepts": ["algebra"],
            "status": "completed"
        }
    })
)

result = json.loads(response['Body'].read().decode())
print(result)
```

## Configuration

### GitHub Secrets (Required)
- `AWS_ACCESS_KEY_ID` - AWS access key
- `AWS_SECRET_ACCESS_KEY` - AWS secret key
- `SAGEMAKER_ROLE_ARN` - SageMaker execution role ARN

### Environment Variables
Edit `.github/workflows/deploy-sagemaker.yml`:
```yaml
env:
  AWS_REGION: us-east-1
  ECR_REPOSITORY: ai-service-sagemaker
  SAGEMAKER_ENDPOINT_NAME: ai-service-endpoint
```

## Monitoring

```bash
# Check deployment status
aws sagemaker describe-endpoint --endpoint-name ai-service-endpoint

# View logs
aws logs tail /aws/sagemaker/Endpoints/ai-service-endpoint --follow
```

## Cost Optimization

| Instance | $/hour | $/month (24/7) | Recommendation |
|----------|--------|----------------|----------------|
| ml.t2.medium | $0.065 | $47 | Dev/Test |
| ml.m5.large | $0.134 | $97 | Production |

**Tip**: Delete endpoint when not in use, redeploy with `git push` when needed (5-10 min).
## References
- [SageMaker Deployment Guide](SAGEMAKER_DEPLOYMENT.md)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [AWS SageMaker](https://docs.aws.amazon.com/sagemaker/)
- [GitHub Actions](https://docs.github.com/en/actions)

