# AWS Deployment Makefile for Comments System
# Provides convenient commands for AWS deployment operations

# Configuration
PROJECT_NAME := comments-system
ENVIRONMENT := production
AWS_REGION := us-east-1
AWS_PROFILE := default

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

# Help target
.PHONY: help
help: ## Show this help message
	@echo "$(BLUE)AWS Deployment Commands for $(PROJECT_NAME)$(NC)"
	@echo "============================================"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(BLUE)Examples:$(NC)"
	@echo "  make deploy          # Full deployment"
	@echo "  make status          # Check deployment status"
	@echo "  make logs            # View recent logs"
	@echo "  make cleanup         # Delete all resources"

# Prerequisites check
.PHONY: check-prereqs
check-prereqs: ## Check deployment prerequisites
	@echo "$(BLUE)[INFO]$(NC) Checking prerequisites..."
	@command -v aws >/dev/null 2>&1 || { echo "$(RED)[ERROR]$(NC) AWS CLI not found"; exit 1; }
	@command -v docker >/dev/null 2>&1 || { echo "$(RED)[ERROR]$(NC) Docker not found"; exit 1; }
	@aws sts get-caller-identity --profile $(AWS_PROFILE) >/dev/null 2>&1 || { echo "$(RED)[ERROR]$(NC) AWS credentials not configured"; exit 1; }
	@echo "$(GREEN)[SUCCESS]$(NC) All prerequisites met!"

# Generate secrets
.PHONY: secrets
secrets: ## Generate secure secrets for deployment
	@echo "$(BLUE)[INFO]$(NC) Generating secure secrets..."
	@mkdir -p aws-deployment
	@python3 -c "import secrets; print(f'DJANGO_SECRET_KEY={secrets.token_urlsafe(50)}')" > aws-deployment/secrets.env
	@python3 -c "import secrets; print(f'DB_PASSWORD={secrets.token_urlsafe(16)}')" >> aws-deployment/secrets.env
	@echo "$(GREEN)[SUCCESS]$(NC) Secrets generated in aws-deployment/secrets.env"
	@echo "$(YELLOW)[WARNING]$(NC) Keep this file secure!"

# Build and push images
.PHONY: build-images
build-images: check-prereqs ## Build and push Docker images to ECR
	@echo "$(BLUE)[INFO]$(NC) Building and pushing Docker images..."
	@AWS_ACCOUNT_ID=$$(aws sts get-caller-identity --query Account --output text --profile $(AWS_PROFILE)); \
	echo "Account ID: $$AWS_ACCOUNT_ID"; \
	aws ecr get-login-password --region $(AWS_REGION) --profile $(AWS_PROFILE) | docker login --username AWS --password-stdin $$AWS_ACCOUNT_ID.dkr.ecr.$(AWS_REGION).amazonaws.com; \
	docker build -f backend/Dockerfile.aws -t $(PROJECT_NAME)/backend:latest backend/; \
	docker tag $(PROJECT_NAME)/backend:latest $$AWS_ACCOUNT_ID.dkr.ecr.$(AWS_REGION).amazonaws.com/$(PROJECT_NAME)/backend:latest; \
	docker push $$AWS_ACCOUNT_ID.dkr.ecr.$(AWS_REGION).amazonaws.com/$(PROJECT_NAME)/backend:latest; \
	docker build -f frontend/Dockerfile.aws -t $(PROJECT_NAME)/frontend:latest frontend/; \
	docker tag $(PROJECT_NAME)/frontend:latest $$AWS_ACCOUNT_ID.dkr.ecr.$(AWS_REGION).amazonaws.com/$(PROJECT_NAME)/frontend:latest; \
	docker push $$AWS_ACCOUNT_ID.dkr.ecr.$(AWS_REGION).amazonaws.com/$(PROJECT_NAME)/frontend:latest
	@echo "$(GREEN)[SUCCESS]$(NC) Images built and pushed to ECR!"

# Deploy infrastructure
.PHONY: deploy-infra
deploy-infra: check-prereqs secrets ## Deploy AWS infrastructure
	@echo "$(BLUE)[INFO]$(NC) Deploying AWS infrastructure..."
	@source aws-deployment/secrets.env && \
	aws cloudformation deploy \
		--template-file aws-deployment/cloudformation-template.yml \
		--stack-name $(PROJECT_NAME)-$(ENVIRONMENT)-infrastructure \
		--parameter-overrides \
			ProjectName=$(PROJECT_NAME) \
			Environment=$(ENVIRONMENT) \
			DBUsername=comments_admin \
			DBPassword=$$DB_PASSWORD \
			DomainName=comments.example.com \
		--capabilities CAPABILITY_NAMED_IAM \
		--region $(AWS_REGION) \
		--profile $(AWS_PROFILE)
	@echo "$(GREEN)[SUCCESS]$(NC) Infrastructure deployed!"

# Deploy services
.PHONY: deploy-services
deploy-services: check-prereqs ## Deploy ECS services
	@echo "$(BLUE)[INFO]$(NC) Deploying ECS services..."
	@if [ ! -f aws-deployment/secrets.env ]; then echo "$(RED)[ERROR]$(NC) Secrets file not found. Run 'make secrets' first."; exit 1; fi
	@AWS_ACCOUNT_ID=$$(aws sts get-caller-identity --query Account --output text --profile $(AWS_PROFILE)); \
	DB_ENDPOINT=$$(aws cloudformation describe-stacks --stack-name $(PROJECT_NAME)-$(ENVIRONMENT)-infrastructure --query 'Stacks[0].Outputs[?OutputKey==`DatabaseEndpoint`].OutputValue' --output text --region $(AWS_REGION) --profile $(AWS_PROFILE)); \
	REDIS_ENDPOINT=$$(aws cloudformation describe-stacks --stack-name $(PROJECT_NAME)-$(ENVIRONMENT)-infrastructure --query 'Stacks[0].Outputs[?OutputKey==`RedisEndpoint`].OutputValue' --output text --region $(AWS_REGION) --profile $(AWS_PROFILE)); \
	S3_BUCKET=$$(aws cloudformation describe-stacks --stack-name $(PROJECT_NAME)-$(ENVIRONMENT)-infrastructure --query 'Stacks[0].Outputs[?OutputKey==`S3BucketName`].OutputValue' --output text --region $(AWS_REGION) --profile $(AWS_PROFILE)); \
	source aws-deployment/secrets.env && \
	aws cloudformation deploy \
		--template-file aws-deployment/ecs-services.yml \
		--stack-name $(PROJECT_NAME)-$(ENVIRONMENT)-services \
		--parameter-overrides \
			ProjectName=$(PROJECT_NAME) \
			Environment=$(ENVIRONMENT) \
			BackendImageURI=$$AWS_ACCOUNT_ID.dkr.ecr.$(AWS_REGION).amazonaws.com/$(PROJECT_NAME)/backend:latest \
			FrontendImageURI=$$AWS_ACCOUNT_ID.dkr.ecr.$(AWS_REGION).amazonaws.com/$(PROJECT_NAME)/frontend:latest \
			DatabaseEndpoint=$$DB_ENDPOINT \
			RedisEndpoint=$$REDIS_ENDPOINT \
			DBUsername=comments_admin \
			DBPassword=$$DB_PASSWORD \
			DjangoSecretKey=$$DJANGO_SECRET_KEY \
			S3BucketName=$$S3_BUCKET \
		--capabilities CAPABILITY_IAM \
		--region $(AWS_REGION) \
		--profile $(AWS_PROFILE)
	@echo "$(GREEN)[SUCCESS]$(NC) Services deployed!"

# Full deployment
.PHONY: deploy
deploy: deploy-infra build-images deploy-services migrate ## Full deployment pipeline
	@echo "$(GREEN)[SUCCESS]$(NC) Full deployment completed!"
	@make status

# Run database migrations
.PHONY: migrate
migrate: ## Run database migrations
	@echo "$(BLUE)[INFO]$(NC) Running database migrations..."
	@sleep 30  # Wait for services to start
	@CLUSTER_NAME="$(PROJECT_NAME)-$(ENVIRONMENT)-cluster"; \
	SERVICE_NAME="$(PROJECT_NAME)-$(ENVIRONMENT)-backend"; \
	TASK_ARN=$$(aws ecs list-tasks --cluster $$CLUSTER_NAME --service-name $$SERVICE_NAME --query 'taskArns[0]' --output text --region $(AWS_REGION) --profile $(AWS_PROFILE)); \
	if [ "$$TASK_ARN" != "None" ] && [ "$$TASK_ARN" != "" ]; then \
		echo "$(BLUE)[INFO]$(NC) Running migrations on task: $$TASK_ARN"; \
		aws ecs execute-command --cluster $$CLUSTER_NAME --task $$TASK_ARN --container backend --command "python manage.py migrate" --interactive --region $(AWS_REGION) --profile $(AWS_PROFILE); \
	else \
		echo "$(YELLOW)[WARNING]$(NC) No running tasks found. Migrations will run automatically."; \
	fi

# Create superuser
.PHONY: superuser
superuser: ## Create Django superuser
	@echo "$(BLUE)[INFO]$(NC) Creating Django superuser..."
	@CLUSTER_NAME="$(PROJECT_NAME)-$(ENVIRONMENT)-cluster"; \
	SERVICE_NAME="$(PROJECT_NAME)-$(ENVIRONMENT)-backend"; \
	TASK_ARN=$$(aws ecs list-tasks --cluster $$CLUSTER_NAME --service-name $$SERVICE_NAME --query 'taskArns[0]' --output text --region $(AWS_REGION) --profile $(AWS_PROFILE)); \
	if [ "$$TASK_ARN" != "None" ] && [ "$$TASK_ARN" != "" ]; then \
		echo "$(BLUE)[INFO]$(NC) Creating superuser on task: $$TASK_ARN"; \
		aws ecs execute-command --cluster $$CLUSTER_NAME --task $$TASK_ARN --container backend --command "python manage.py createsuperuser" --interactive --region $(AWS_REGION) --profile $(AWS_PROFILE); \
	else \
		echo "$(RED)[ERROR]$(NC) No running tasks found."; \
	fi

# Check deployment status
.PHONY: status
status: ## Check deployment status
	@echo "$(BLUE)[INFO]$(NC) Checking deployment status..."
	@INFRA_STATUS=$$(aws cloudformation describe-stacks --stack-name $(PROJECT_NAME)-$(ENVIRONMENT)-infrastructure --query 'Stacks[0].StackStatus' --output text --region $(AWS_REGION) --profile $(AWS_PROFILE) 2>/dev/null || echo "NOT_FOUND"); \
	SERVICES_STATUS=$$(aws cloudformation describe-stacks --stack-name $(PROJECT_NAME)-$(ENVIRONMENT)-services --query 'Stacks[0].StackStatus' --output text --region $(AWS_REGION) --profile $(AWS_PROFILE) 2>/dev/null || echo "NOT_FOUND"); \
	echo ""; \
	echo "$(BLUE) Deployment Status:$(NC)"; \
	echo "   Infrastructure Stack: $$INFRA_STATUS"; \
	echo "   Services Stack: $$SERVICES_STATUS"; \
	echo ""; \
	if [ "$$SERVICES_STATUS" = "CREATE_COMPLETE" ] || [ "$$SERVICES_STATUS" = "UPDATE_COMPLETE" ]; then \
		APP_URL=$$(aws cloudformation describe-stacks --stack-name $(PROJECT_NAME)-$(ENVIRONMENT)-services --query 'Stacks[0].Outputs[?OutputKey==`ApplicationURL`].OutputValue' --output text --region $(AWS_REGION) --profile $(AWS_PROFILE)); \
		if [ "$$APP_URL" != "" ]; then \
			echo "$(GREEN)🚀 Application deployed successfully!$(NC)"; \
			echo ""; \
			echo "Application URL: $$APP_URL"; \
			echo "Admin Panel: $$APP_URL/admin/"; \
			echo "API Docs: $$APP_URL/api/docs/"; \
			echo ""; \
		fi; \
	fi

# Health check
.PHONY: health
health: ## Run application health checks
	@./aws-health-check.sh

# View logs
.PHONY: logs
logs: ## View recent application logs
	@echo "$(BLUE)[INFO]$(NC) Viewing recent logs..."
	@echo "Backend logs:"
	@aws logs tail /ecs/$(PROJECT_NAME)-$(ENVIRONMENT)-backend --since 1h --region $(AWS_REGION) --profile $(AWS_PROFILE) || echo "No backend logs found"
	@echo ""
	@echo "Frontend logs:"
	@aws logs tail /ecs/$(PROJECT_NAME)-$(ENVIRONMENT)-frontend --since 1h --region $(AWS_REGION) --profile $(AWS_PROFILE) || echo "No frontend logs found"

# Scale services
.PHONY: scale
scale: ## Scale services (usage: make scale BACKEND_COUNT=3 FRONTEND_COUNT=2)
	@BACKEND_COUNT?=2
	@FRONTEND_COUNT?=2
	@echo "$(BLUE)[INFO]$(NC) Scaling services..."
	@aws ecs update-service --cluster $(PROJECT_NAME)-$(ENVIRONMENT)-cluster --service $(PROJECT_NAME)-$(ENVIRONMENT)-backend --desired-count $(BACKEND_COUNT) --region $(AWS_REGION) --profile $(AWS_PROFILE)
	@aws ecs update-service --cluster $(PROJECT_NAME)-$(ENVIRONMENT)-cluster --service $(PROJECT_NAME)-$(ENVIRONMENT)-frontend --desired-count $(FRONTEND_COUNT) --region $(AWS_REGION) --profile $(AWS_PROFILE)
	@echo "$(GREEN)[SUCCESS]$(NC) Services scaled: Backend=$(BACKEND_COUNT), Frontend=$(FRONTEND_COUNT)"

# Update application
.PHONY: update
update: build-images ## Update application with new images
	@echo "$(BLUE)[INFO]$(NC) Updating services with new images..."
	@aws ecs update-service --cluster $(PROJECT_NAME)-$(ENVIRONMENT)-cluster --service $(PROJECT_NAME)-$(ENVIRONMENT)-backend --force-new-deployment --region $(AWS_REGION) --profile $(AWS_PROFILE)
	@aws ecs update-service --cluster $(PROJECT_NAME)-$(ENVIRONMENT)-cluster --service $(PROJECT_NAME)-$(ENVIRONMENT)-frontend --force-new-deployment --region $(AWS_REGION) --profile $(AWS_PROFILE)
	@echo "$(GREEN)[SUCCESS]$(NC) Services updated!"

# Cleanup
.PHONY: cleanup
cleanup: ## Delete all AWS resources
	@echo "$(YELLOW)[WARNING]$(NC) This will delete ALL AWS resources!"
	@read -p "Are you sure? (yes/no): " confirm && [ "$$confirm" = "yes" ] || exit 1
	@echo "$(BLUE)[INFO]$(NC) Deleting services stack..."
	@aws cloudformation delete-stack --stack-name $(PROJECT_NAME)-$(ENVIRONMENT)-services --region $(AWS_REGION) --profile $(AWS_PROFILE) 2>/dev/null || true
	@echo "$(BLUE)[INFO]$(NC) Waiting for services stack deletion..."
	@aws cloudformation wait stack-delete-complete --stack-name $(PROJECT_NAME)-$(ENVIRONMENT)-services --region $(AWS_REGION) --profile $(AWS_PROFILE) 2>/dev/null || true
	@echo "$(BLUE)[INFO]$(NC) Deleting infrastructure stack..."
	@aws cloudformation delete-stack --stack-name $(PROJECT_NAME)-$(ENVIRONMENT)-infrastructure --region $(AWS_REGION) --profile $(AWS_PROFILE) 2>/dev/null || true
	@echo "$(BLUE)[INFO]$(NC) Waiting for infrastructure stack deletion..."
	@aws cloudformation wait stack-delete-complete --stack-name $(PROJECT_NAME)-$(ENVIRONMENT)-infrastructure --region $(AWS_REGION) --profile $(AWS_PROFILE) 2>/dev/null || true
	@echo "$(GREEN)[SUCCESS]$(NC) All AWS resources deleted!"

# Cost estimation
.PHONY: cost
cost: ## Show estimated monthly costs
	@echo "$(BLUE) Estimated Monthly AWS Costs:$(NC)"
	@echo "================================"
	@echo " ECS Fargate (2 tasks):     ~$$35-50"
	@echo " RDS PostgreSQL (t3.micro): ~$$15-20"
	@echo " ElastiCache Redis (t3.micro): ~$$15-20"
	@echo " Application Load Balancer: ~$$20-25"
	@echo " S3 Storage & Data Transfer:  ~$$5-10"
	@echo " CloudWatch Logs & Metrics:   ~$$5-10"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo " Total Estimated Cost:      ~$$95-135/month"
	@echo ""
	@echo "$(YELLOW) Cost Optimization Tips:$(NC)"
	@echo "• Use Spot instances for non-critical workloads"
	@echo "• Configure auto-scaling to reduce costs during low traffic"
	@echo "• Monitor AWS Cost Explorer regularly"
	@echo "• Consider Reserved Instances for long-term deployments"

# Debug mode
.PHONY: debug
debug: ## Enable debug mode and show detailed information
	@echo "$(BLUE) Debug Information:$(NC)"
	@echo "====================="
	@echo "Project: $(PROJECT_NAME)"
	@echo "Environment: $(ENVIRONMENT)"
	@echo "AWS Region: $(AWS_REGION)"
	@echo "AWS Profile: $(AWS_PROFILE)"
	@echo ""
	@echo "$(BLUE)AWS Account Info:$(NC)"
	@aws sts get-caller-identity --profile $(AWS_PROFILE)
	@echo ""
	@echo "$(BLUE)CloudFormation Stacks:$(NC)"
	@aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE --query 'StackSummaries[?contains(StackName,`$(PROJECT_NAME)`)].{Name:StackName,Status:StackStatus,Created:CreationTime}' --output table --region $(AWS_REGION) --profile $(AWS_PROFILE)

# Default target
.DEFAULT_GOAL := help