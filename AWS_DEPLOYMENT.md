# AWS Production Deployment Guide

## Complete AWS Deployment for Comments System

This guide provides step-by-step instructions for deploying the multi-tiered comments system to AWS using ECS Fargate, RDS PostgreSQL, and ElastiCache Redis.

## Prerequisites

### 1. AWS Account Setup

- AWS account with administrative access
- AWS CLI installed and configured
- Docker installed locally
- Basic knowledge of AWS services

### 2. Required Tools

```bash
# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Configure AWS CLI
aws configure
# Enter your AWS Access Key ID, Secret Access Key, Region, and Output format
```

### 3. Cost Estimation

**Monthly AWS costs (approximate):**

- ECS Fargate: $30-50
- RDS PostgreSQL (db.t3.micro): $15-20
- ElastiCache Redis (cache.t3.micro): $15-20
- Application Load Balancer: $20-25
- Data transfer and storage: $5-10
- **Total: ~$85-125/month**

## Architecture Overview

``
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   CloudFront    │────│  Load Balancer  │────│   ECS Cluster   │
│   (Optional)    │    │      (ALB)      │    │   (Fargate)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │                         │
                              │                         │
                       ┌─────────────────┐    ┌─────────────────┐
                       │   Frontend      │    │   Backend       │
                       │   (Nginx)       │    │   (Django)      │
                       └─────────────────┘    └─────────────────┘
                                                        │
                                               ┌─────────────────┐
                                               │   PostgreSQL    │
                                               │     (RDS)       │
                                               └─────────────────┘
                                                        │
                                               ┌─────────────────┐
                                               │     Redis       │
                                               │ (ElastiCache)   │
                                               └─────────────────┘
``

## Quick Deployment

### 1. Clone and Prepare

```bash
# Make deployment script executable
chmod +x deploy-aws.sh
chmod +x aws-health-check.sh

# Run full deployment
./deploy-aws.sh
```

The script will:

1. Check prerequisites
2. Generate secure secrets
3. Build and push Docker images
4. Deploy AWS infrastructure
5. Deploy ECS services
6. Run database migrations
7. Show deployment status

### 2. Create Admin User

```bash
# After deployment completes
./deploy-aws.sh superuser
```

### 3. Check Status

```bash
# Quick health check
./aws-health-check.sh

# Detailed status
./deploy-aws.sh status
```

## Manual Deployment Steps

### Step 1: Deploy Infrastructure

```bash
# Deploy infrastructure stack
aws cloudformation deploy \
    --template-file aws-deployment/cloudformation-template.yml \
    --stack-name comments-system-production-infrastructure \
    --parameter-overrides \
        ProjectName=comments-system \
        Environment=production \
        DBUsername=comments_admin \
        DBPassword=YOUR_SECURE_PASSWORD \
    --capabilities CAPABILITY_NAMED_IAM \
    --region us-east-1
```

### Step 2: Build and Push Images

```bash
# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=us-east-1

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Build and push backend
docker build -f backend/Dockerfile.aws -t comments-system/backend:latest backend/
docker tag comments-system/backend:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/comments-system/backend:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/comments-system/backend:latest

# Build and push frontend
docker build -f frontend/Dockerfile.aws -t comments-system/frontend:latest frontend/
docker tag comments-system/frontend:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/comments-system/frontend:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/comments-system/frontend:latest
```

### Step 3: Deploy Services

```bash
# Get infrastructure outputs
DB_ENDPOINT=$(aws cloudformation describe-stacks --stack-name comments-system-production-infrastructure --query 'Stacks[0].Outputs[?OutputKey==`DatabaseEndpoint`].OutputValue' --output text)
REDIS_ENDPOINT=$(aws cloudformation describe-stacks --stack-name comments-system-production-infrastructure --query 'Stacks[0].Outputs[?OutputKey==`RedisEndpoint`].OutputValue' --output text)
S3_BUCKET=$(aws cloudformation describe-stacks --stack-name comments-system-production-infrastructure --query 'Stacks[0].Outputs[?OutputKey==`S3BucketName`].OutputValue' --output text)

# Deploy services
aws cloudformation deploy \
    --template-file aws-deployment/ecs-services.yml \
    --stack-name comments-system-production-services \
    --parameter-overrides \
        ProjectName=comments-system \
        Environment=production \
        BackendImageURI=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/comments-system/backend:latest \
        FrontendImageURI=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/comments-system/frontend:latest \
        DatabaseEndpoint=$DB_ENDPOINT \
        RedisEndpoint=$REDIS_ENDPOINT \
        DBUsername=comments_admin \
        DBPassword=YOUR_SECURE_PASSWORD \
        DjangoSecretKey=YOUR_DJANGO_SECRET_KEY \
        S3BucketName=$S3_BUCKET \
    --capabilities CAPABILITY_IAM \
    --region us-east-1
```

## Configuration Details

### Environment Variables

The deployment uses the following key environment variables:

**Backend (Django):**

- `DJANGO_SETTINGS_MODULE`: `comments_project.settings.production`
- `DATABASE_URL`: Auto-generated from RDS endpoint
- `REDIS_URL`: Auto-generated from ElastiCache endpoint
- `SECRET_KEY`: Auto-generated secure key
- `AWS_STORAGE_BUCKET_NAME`: S3 bucket for static files

**Frontend (Vue.js):**

- `NODE_ENV`: `production`
- `VUE_APP_API_BASE_URL`: `/api` (proxied by ALB)

### Security Features

- All traffic encrypted in transit
- Security groups restrict access
- Secrets managed securely
- No public database access
- Auto-scaling enabled
- Health checks configured

## Monitoring and Maintenance

### Health Checks

```bash
# Application health
curl http://YOUR-ALB-DNS/api/health/

# Service status
./aws-health-check.sh
```

### Logs Access

```bash
# Backend logs
aws logs tail /ecs/comments-system-production-backend --follow

# Frontend logs
aws logs tail /ecs/comments-system-production-frontend --follow
```

### Scaling

```bash
# Scale backend service
aws ecs update-service \
    --cluster comments-system-production-cluster \
    --service comments-system-production-backend \
    --desired-count 3
```

### Database Management

```bash
# Connect to running task for database operations
CLUSTER_NAME="comments-system-production-cluster"
SERVICE_NAME="comments-system-production-backend"
TASK_ARN=$(aws ecs list-tasks --cluster $CLUSTER_NAME --service-name $SERVICE_NAME --query 'taskArns[0]' --output text)

# Run migrations
aws ecs execute-command \
    --cluster $CLUSTER_NAME \
    --task $TASK_ARN \
    --container backend \
    --command "python manage.py migrate" \
    --interactive

# Create superuser
aws ecs execute-command \
    --cluster $CLUSTER_NAME \
    --task $TASK_ARN \
    --container backend \
    --command "python manage.py createsuperuser" \
    --interactive
```

## Post-Deployment Steps

### 1. Domain Configuration

```bash
# Get Load Balancer DNS
ALB_DNS=$(aws cloudformation describe-stacks --stack-name comments-system-production-infrastructure --query 'Stacks[0].Outputs[?OutputKey==`ALBDNS`].OutputValue' --output text)

# Configure your domain DNS:
# Create CNAME record: your-domain.com -> $ALB_DNS
```

### 2. SSL Certificate (Optional)

```bash
# Request SSL certificate
aws acm request-certificate \
    --domain-name your-domain.com \
    --validation-method DNS \
    --region us-east-1

# Add HTTPS listener to ALB after certificate validation
```

### 3. CloudFront Distribution (Optional)

For global content delivery, consider adding CloudFront:

- Lower latency worldwide
- DDoS protection
- SSL termination
- Caching static assets

## Updates and Deployments

### Code Updates

```bash
# 1. Build new images
docker build -f backend/Dockerfile.aws -t comments-system/backend:v2.0 backend/
docker build -f frontend/Dockerfile.aws -t comments-system/frontend:v2.0 frontend/

# 2. Push to ECR
docker tag comments-system/backend:v2.0 $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/comments-system/backend:v2.0
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/comments-system/backend:v2.0

# 3. Update service
aws ecs update-service \
    --cluster comments-system-production-cluster \
    --service comments-system-production-backend \
    --force-new-deployment
```

### Infrastructure Updates

```bash
# Update CloudFormation stack
aws cloudformation deploy \
    --template-file aws-deployment/cloudformation-template.yml \
    --stack-name comments-system-production-infrastructure \
    --capabilities CAPABILITY_NAMED_IAM
```

## Cleanup

```bash
# Delete all resources
./deploy-aws.sh cleanup

# Or manually:
aws cloudformation delete-stack --stack-name comments-system-production-services
aws cloudformation delete-stack --stack-name comments-system-production-infrastructure
```

## Troubleshooting

### Common Issues

**Service not starting:**

```bash
# Check service events
aws ecs describe-services \
    --cluster comments-system-production-cluster \
    --services comments-system-production-backend
```

**Database connection issues:**

```bash
# Check security groups and RDS status
aws rds describe-db-instances --db-instance-identifier comments-system-production-postgres
```

**Image pull errors:**

```bash
# Verify ECR repositories exist
aws ecr describe-repositories
```

### Support

- CloudWatch Logs for application logs
- CloudTrail for API activity
- CloudWatch Metrics for performance
- CloudWatch Alarms for monitoring

## Additional Resources

- [AWS ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [AWS RDS Documentation](https://docs.aws.amazon.com/rds/)
- [AWS ElastiCache Documentation](https://docs.aws.amazon.com/elasticache/)
- [Django on AWS Best Practices](https://aws.amazon.com/getting-started/hands-on/deploy-python-application/)

---

**Congratulations!** Your multi-tiered comments system is now running on AWS with enterprise-grade reliability, security, and scalability.
