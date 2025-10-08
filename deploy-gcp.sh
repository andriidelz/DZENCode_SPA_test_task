#!/bin/bash

# Production deployment script for Google Cloud Platform

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN} Deploying Comment System to Google Cloud Platform...${NC}"

# Check required environment variables
required_vars=("PROJECT_ID" "REGION" "SERVICE_NAME")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo -e "${RED} Environment variable $var is not set${NC}"
        exit 1
    fi
done

# gcloud CLI check
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED} gcloud CLI is not installed${NC}"
    exit 1
fi

echo -e "${YELLOW} Configuration:${NC}"
echo -e "   Project ID: $PROJECT_ID"
echo -e "   Region: $REGION"
echo -e "   Service: $SERVICE_NAME"

# Set project
gcloud config set project $PROJECT_ID

# Enable required APIs
echo -e "${YELLOW} Enabling required APIs...${NC}"
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable sql-component.googleapis.com
gcloud services enable redis.googleapis.com

# Build and submit backend image
echo -e "${YELLOW} Building and submitting backend image...${NC}"
gcloud builds submit --tag gcr.io/$PROJECT_ID/comment-system-backend backend/ --file=backend/Dockerfile.prod

# Build and submit frontend image
echo -e "${YELLOW} Building and submitting frontend image...${NC}"
gcloud builds submit --tag gcr.io/$PROJECT_ID/comment-system-frontend frontend/ --file=frontend/Dockerfile.prod

# Deploy backend to Cloud Run
echo -e "${YELLOW} Deploying backend to Cloud Run...${NC}"
gcloud run deploy $SERVICE_NAME-backend \
    --image gcr.io/$PROJECT_ID/comment-system-backend \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --set-env-vars="DEBUG=0,ALLOWED_HOSTS=*" \
    --memory=1Gi \
    --cpu=1 \
    --min-instances=1 \
    --max-instances=10

# Deploy frontend to Cloud Run
echo -e "${YELLOW} Deploying frontend to Cloud Run...${NC}"
gcloud run deploy $SERVICE_NAME-frontend \
    --image gcr.io/$PROJECT_ID/comment-system-frontend \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --memory=512Mi \
    --cpu=1 \
    --min-instances=1 \
    --max-instances=5

# Get service URLs
BACKEND_URL=$(gcloud run services describe $SERVICE_NAME-backend --platform managed --region $REGION --format 'value(status.url)')
FRONTEND_URL=$(gcloud run services describe $SERVICE_NAME-frontend --platform managed --region $REGION --format 'value(status.url)')

echo -e "${GREEN} Deployment completed successfully!${NC}"
echo -e "${GREEN} Backend URL: $BACKEND_URL${NC}"
echo -e "${GREEN} Frontend URL: $FRONTEND_URL${NC}"

# Show service status
echo -e "${YELLOW} Service Status:${NC}"
gcloud run services list --platform managed --region $REGION --filter="metadata.name:$SERVICE_NAME"
