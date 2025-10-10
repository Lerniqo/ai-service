#!/bin/bash

# Manual deployment script for AI Service to SageMaker
# Usage: ./deploy-to-sagemaker.sh [environment] [region]
# Example: ./deploy-to-sagemaker.sh dev eu-north-1

set -e

# Default values
ENVIRONMENT=${1:-dev}
AWS_REGION=${2:-eu-north-1}
PROJECT_NAME="webapp"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting AI Service deployment to SageMaker${NC}"
echo "Environment: $ENVIRONMENT"
echo "Region: $AWS_REGION"
echo "Project: $PROJECT_NAME"
echo "----------------------------------------"

# Check if AWS CLI is configured
if ! aws sts get-caller-identity >/dev/null 2>&1; then
    echo -e "${RED}❌ AWS CLI not configured. Please run 'aws configure' first${NC}"
    exit 1
fi

# Set variables
ECR_REPOSITORY="${PROJECT_NAME}-${ENVIRONMENT}-ai-service"
ENDPOINT_NAME="${PROJECT_NAME}-${ENVIRONMENT}-ai-service-endpoint"
IMAGE_TAG=$(git rev-parse --short HEAD 2>/dev/null || echo "manual-$(date +%s)")

echo -e "${YELLOW}📦 Building and pushing Docker image...${NC}"

# Get ECR login
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $(aws sts get-caller-identity --query Account --output text).dkr.ecr.$AWS_REGION.amazonaws.com

# Build and push image
ECR_REGISTRY=$(aws sts get-caller-identity --query Account --output text).dkr.ecr.$AWS_REGION.amazonaws.com
docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
docker tag $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG $ECR_REGISTRY/$ECR_REPOSITORY:latest

docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
docker push $ECR_REGISTRY/$ECR_REPOSITORY:latest

echo -e "${GREEN}✅ Image pushed successfully${NC}"

# Update SageMaker endpoint
echo -e "${YELLOW}🔄 Updating SageMaker endpoint...${NC}"

# Check if endpoint exists
if aws sagemaker describe-endpoint --endpoint-name $ENDPOINT_NAME --region $AWS_REGION >/dev/null 2>&1; then
    echo "SageMaker endpoint exists. Updating with new image..."
    
    # Create new model with updated image
    MODEL_NAME="${PROJECT_NAME}-${ENVIRONMENT}-ai-service-model-$(date +%s)"
    
    # Get the execution role ARN from the existing model
    CURRENT_MODEL=$(aws sagemaker list-models --name-contains "${PROJECT_NAME}-${ENVIRONMENT}-ai-service-model" --region $AWS_REGION --query 'Models[0].ModelName' --output text)
    EXECUTION_ROLE_ARN=$(aws sagemaker describe-model --model-name $CURRENT_MODEL --region $AWS_REGION --query 'ExecutionRoleArn' --output text)
    
    # Get VPC configuration from existing model
    VPC_CONFIG=$(aws sagemaker describe-model --model-name $CURRENT_MODEL --region $AWS_REGION --query 'VpcConfig')
    
    # Create new model with updated image
    if [ "$VPC_CONFIG" != "null" ]; then
        aws sagemaker create-model \
            --model-name $MODEL_NAME \
            --primary-container "Image=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG,Environment={PYTHONUNBUFFERED=1,SAGEMAKER_PROGRAM=serve,SAGEMAKER_SUBMIT_DIRECTORY=/opt/ml/code}" \
            --execution-role-arn $EXECUTION_ROLE_ARN \
            --vpc-config "$VPC_CONFIG" \
            --region $AWS_REGION
    else
        aws sagemaker create-model \
            --model-name $MODEL_NAME \
            --primary-container "Image=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG,Environment={PYTHONUNBUFFERED=1,SAGEMAKER_PROGRAM=serve,SAGEMAKER_SUBMIT_DIRECTORY=/opt/ml/code}" \
            --execution-role-arn $EXECUTION_ROLE_ARN \
            --region $AWS_REGION
    fi
    
    # Create new endpoint configuration
    CONFIG_NAME="${PROJECT_NAME}-${ENVIRONMENT}-ai-service-config-$(date +%s)"
    aws sagemaker create-endpoint-configuration \
        --endpoint-config-name $CONFIG_NAME \
        --production-variants "VariantName=AllTraffic,ModelName=$MODEL_NAME,InitialInstanceCount=1,InstanceType=ml.m5.large,InitialVariantWeight=1.0" \
        --region $AWS_REGION
    
    # Update endpoint
    aws sagemaker update-endpoint \
        --endpoint-name $ENDPOINT_NAME \
        --endpoint-config-name $CONFIG_NAME \
        --region $AWS_REGION
    
    echo -e "${GREEN}✅ SageMaker endpoint update initiated${NC}"
    echo -e "${YELLOW}⏳ This may take 5-10 minutes to complete...${NC}"
    
else
    echo -e "${RED}❌ SageMaker endpoint does not exist. Please run Terraform first:${NC}"
    echo "cd ../terraform-infra/environments/$ENVIRONMENT"
    echo "terraform apply -var-file=terraform.tfvars"
    exit 1
fi

# Optional: Wait for endpoint to be ready (commented out to avoid long waits)
# echo -e "${YELLOW}⏳ Waiting for endpoint to be updated...${NC}"
# aws sagemaker wait endpoint-in-service --endpoint-name $ENDPOINT_NAME --region $AWS_REGION

# Get endpoint status
STATUS=$(aws sagemaker describe-endpoint --endpoint-name $ENDPOINT_NAME --region $AWS_REGION --query 'EndpointStatus' --output text)
echo "Current endpoint status: $STATUS"

if [ "$STATUS" = "InService" ]; then
    echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
elif [ "$STATUS" = "Updating" ]; then
    echo -e "${YELLOW}🔄 Endpoint is updating... Check AWS Console for progress${NC}"
else
    echo -e "${RED}⚠️ Endpoint status is $STATUS. Check AWS Console for details.${NC}"
fi

echo "----------------------------------------"
echo -e "${GREEN}🎉 Deployment process completed${NC}"
echo "API Gateway URL: https://[YOUR-API-GATEWAY-ID].execute-api.$AWS_REGION.amazonaws.com/$ENVIRONMENT/api/ai-service"
echo "Monitor the deployment in AWS Console: https://$AWS_REGION.console.aws.amazon.com/sagemaker/home?region=$AWS_REGION#/endpoints"