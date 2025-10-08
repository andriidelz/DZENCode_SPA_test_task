#!/bin/bash

# AWS Production Deployment Script
# This script automates the complete deployment process to AWS

set -e

# Configuration
PROJECT_NAME="comments-system"
ENVIRONMENT="production"
AWS_REGION="us-east-1"
AWS_PROFILE="default"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI not found. Please install AWS CLI and configure it."
        exit 1
    fi
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker not found. Please install Docker."
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity --profile "$AWS_PROFILE" &> /dev/null; then
        print_error "AWS credentials not configured properly."
        exit 1
    fi
    
    print_success "All prerequisites met!"
}

# Function to generate secure passwords and keys
generate_secrets() {
    print_status "Generating secure secrets..."
    
    # Generate Django secret key
    DJANGO_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
    
    # Generate database password
    DB_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(16))")
    
    # Save secrets to file (will be used for CloudFormation parameters)
    cat > aws-deployment/secrets.env << EOF
DJANGO_SECRET_KEY=$DJANGO_SECRET_KEY
DB_PASSWORD=$DB_PASSWORD
EOF
    
    print_success "Secrets generated and saved to aws-deployment/secrets.env"
    print_warning "Keep this file secure and do not commit it to version control!"
}

# Function to build and push Docker images
build_and_push_images() {
    print_status "Building and pushing Docker images..."
    
    # Get AWS account ID
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text --profile "$AWS_PROFILE")
    
    # ECR login
    aws ecr get-login-password --region "$AWS_REGION" --profile "$AWS_PROFILE" | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
    
    # Build and push backend image
    print_status "Building backend image..."
    docker build -f backend/Dockerfile.prod -t "$PROJECT_NAME/backend:latest" backend/
    docker tag "$PROJECT_NAME/backend:latest" "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME/backend:latest"
    docker push "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME/backend:latest"
    
    # Build and push frontend image
    print_status "Building frontend image..."
    docker build -f frontend/Dockerfile.prod -t "$PROJECT_NAME/frontend:latest" frontend/
    docker tag "$PROJECT_NAME/frontend:latest" "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME/frontend:latest"
    docker push "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME/frontend:latest"
    
    print_success "Docker images built and pushed to ECR!"
    
    # Save image URIs for CloudFormation
    echo "BACKEND_IMAGE_URI=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME/backend:latest" >> aws-deployment/deployment.env
    echo "FRONTEND_IMAGE_URI=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME/frontend:latest" >> aws-deployment/deployment.env
}

# Function to deploy infrastructure
deploy_infrastructure() {
    print_status "Deploying AWS infrastructure..."
    
    # Load secrets
    source aws-deployment/secrets.env
    
    # Create or update infrastructure stack
    aws cloudformation deploy \
        --template-file aws-deployment/cloudformation-template.yml \
        --stack-name "$PROJECT_NAME-$ENVIRONMENT-infrastructure" \
        --parameter-overrides \
            ProjectName="$PROJECT_NAME" \
            Environment="$ENVIRONMENT" \
            DBUsername="comments_admin" \
            DBPassword="$DB_PASSWORD" \
            DomainName="comments.example.com" \
        --capabilities CAPABILITY_NAMED_IAM \
        --region "$AWS_REGION" \
        --profile "$AWS_PROFILE"
    
    print_success "Infrastructure deployed successfully!"
    
    # Get infrastructure outputs
    print_status "Retrieving infrastructure information..."
    
    DB_ENDPOINT=$(aws cloudformation describe-stacks \
        --stack-name "$PROJECT_NAME-$ENVIRONMENT-infrastructure" \
        --query 'Stacks[0].Outputs[?OutputKey==`DatabaseEndpoint`].OutputValue' \
        --output text \
        --region "$AWS_REGION" \
        --profile "$AWS_PROFILE")
    
    REDIS_ENDPOINT=$(aws cloudformation describe-stacks \
        --stack-name "$PROJECT_NAME-$ENVIRONMENT-infrastructure" \
        --query 'Stacks[0].Outputs[?OutputKey==`RedisEndpoint`].OutputValue' \
        --output text \
        --region "$AWS_REGION" \
        --profile "$AWS_PROFILE")
    
    S3_BUCKET=$(aws cloudformation describe-stacks \
        --stack-name "$PROJECT_NAME-$ENVIRONMENT-infrastructure" \
        --query 'Stacks[0].Outputs[?OutputKey==`S3BucketName`].OutputValue' \
        --output text \
        --region "$AWS_REGION" \
        --profile "$AWS_PROFILE")
    
    # Save infrastructure info
    echo "DB_ENDPOINT=$DB_ENDPOINT" >> aws-deployment/deployment.env
    echo "REDIS_ENDPOINT=$REDIS_ENDPOINT" >> aws-deployment/deployment.env
    echo "S3_BUCKET=$S3_BUCKET" >> aws-deployment/deployment.env
}

# Function to deploy services
deploy_services() {
    print_status "Deploying ECS services..."
    
    # Load deployment environment
    source aws-deployment/deployment.env
    source aws-deployment/secrets.env
    
    # Deploy services stack
    aws cloudformation deploy \
        --template-file aws-deployment/ecs-services.yml \
        --stack-name "$PROJECT_NAME-$ENVIRONMENT-services" \
        --parameter-overrides \
            ProjectName="$PROJECT_NAME" \
            Environment="$ENVIRONMENT" \
            BackendImageURI="$BACKEND_IMAGE_URI" \
            FrontendImageURI="$FRONTEND_IMAGE_URI" \
            DatabaseEndpoint="$DB_ENDPOINT" \
            RedisEndpoint="$REDIS_ENDPOINT" \
            DBUsername="comments_admin" \
            DBPassword="$DB_PASSWORD" \
            DjangoSecretKey="$DJANGO_SECRET_KEY" \
            S3BucketName="$S3_BUCKET" \
        --capabilities CAPABILITY_IAM \
        --region "$AWS_REGION" \
        --profile "$AWS_PROFILE"
    
    print_success "Services deployed successfully!"
}

# Function to run database migrations
run_migrations() {
    print_status "Running database migrations..."
    
    # Get cluster and service information
    CLUSTER_NAME="$PROJECT_NAME-$ENVIRONMENT-cluster"
    SERVICE_NAME="$PROJECT_NAME-$ENVIRONMENT-backend"
    
    # Get a running task ARN
    TASK_ARN=$(aws ecs list-tasks \
        --cluster "$CLUSTER_NAME" \
        --service-name "$SERVICE_NAME" \
        --query 'taskArns[0]' \
        --output text \
        --region "$AWS_REGION" \
        --profile "$AWS_PROFILE")
    
    if [ "$TASK_ARN" != "None" ] && [ "$TASK_ARN" != "" ]; then
        print_status "Running migrations on task: $TASK_ARN"
        
        aws ecs execute-command \
            --cluster "$CLUSTER_NAME" \
            --task "$TASK_ARN" \
            --container backend \
            --command "python manage.py migrate" \
            --interactive \
            --region "$AWS_REGION" \
            --profile "$AWS_PROFILE"
        
        print_success "Database migrations completed!"
    else
        print_warning "No running tasks found. Migrations will run automatically when the service starts."
    fi
}

# Function to create superuser
create_superuser() {
    print_status "Creating Django superuser..."
    
    # Get cluster and service information
    CLUSTER_NAME="$PROJECT_NAME-$ENVIRONMENT-cluster"
    SERVICE_NAME="$PROJECT_NAME-$ENVIRONMENT-backend"
    
    # Get a running task ARN
    TASK_ARN=$(aws ecs list-tasks \
        --cluster "$CLUSTER_NAME" \
        --service-name "$SERVICE_NAME" \
        --query 'taskArns[0]' \
        --output text \
        --region "$AWS_REGION" \
        --profile "$AWS_PROFILE")
    
    if [ "$TASK_ARN" != "None" ] && [ "$TASK_ARN" != "" ]; then
        print_status "Creating superuser on task: $TASK_ARN"
        print_warning "You will be prompted to enter superuser credentials..."
        
        aws ecs execute-command \
            --cluster "$CLUSTER_NAME" \
            --task "$TASK_ARN" \
            --container backend \
            --command "python manage.py createsuperuser" \
            --interactive \
            --region "$AWS_REGION" \
            --profile "$AWS_PROFILE"
        
        print_success "Superuser created successfully!"
    else
        print_error "No running tasks found. Please try again after services are running."
    fi
}

# Function to get application URL
get_application_url() {
    print_status "Getting application URL..."
    
    APP_URL=$(aws cloudformation describe-stacks \
        --stack-name "$PROJECT_NAME-$ENVIRONMENT-services" \
        --query 'Stacks[0].Outputs[?OutputKey==`ApplicationURL`].OutputValue' \
        --output text \
        --region "$AWS_REGION" \
        --profile "$AWS_PROFILE")
    
    if [ "$APP_URL" != "" ]; then
        print_success "Application deployed successfully!"
        echo ""
        echo " Your application is available at: $APP_URL"
        echo " Admin panel: $APP_URL/admin/"
        echo " API documentation: $APP_URL/api/docs/"
        echo ""
    else
        print_error "Could not retrieve application URL. Check CloudFormation console."
    fi
}

# Function to show deployment status
show_status() {
    print_status "Checking deployment status..."
    
    # Check infrastructure stack
    INFRA_STATUS=$(aws cloudformation describe-stacks \
        --stack-name "$PROJECT_NAME-$ENVIRONMENT-infrastructure" \
        --query 'Stacks[0].StackStatus' \
        --output text \
        --region "$AWS_REGION" \
        --profile "$AWS_PROFILE" 2>/dev/null || echo "NOT_FOUND")
    
    # Check services stack
    SERVICES_STATUS=$(aws cloudformation describe-stacks \
        --stack-name "$PROJECT_NAME-$ENVIRONMENT-services" \
        --query 'Stacks[0].StackStatus' \
        --output text \
        --region "$AWS_REGION" \
        --profile "$AWS_PROFILE" 2>/dev/null || echo "NOT_FOUND")
    
    echo ""
    echo " Deployment Status:"
    echo "   Infrastructure Stack: $INFRA_STATUS"
    echo "   Services Stack: $SERVICES_STATUS"
    echo ""
    
    if [ "$SERVICES_STATUS" = "CREATE_COMPLETE" ] || [ "$SERVICES_STATUS" = "UPDATE_COMPLETE" ]; then
        get_application_url
    fi
}

# Function to cleanup deployment
cleanup() {
    print_warning "Cleaning up AWS resources..."
    
    read -p "Are you sure you want to delete all AWS resources? (yes/no): " -r
    if [[ $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        # Delete services stack first
        aws cloudformation delete-stack \
            --stack-name "$PROJECT_NAME-$ENVIRONMENT-services" \
            --region "$AWS_REGION" \
            --profile "$AWS_PROFILE" 2>/dev/null || true
        
        print_status "Waiting for services stack deletion..."
        aws cloudformation wait stack-delete-complete \
            --stack-name "$PROJECT_NAME-$ENVIRONMENT-services" \
            --region "$AWS_REGION" \
            --profile "$AWS_PROFILE" 2>/dev/null || true
        
        # Delete infrastructure stack
        aws cloudformation delete-stack \
            --stack-name "$PROJECT_NAME-$ENVIRONMENT-infrastructure" \
            --region "$AWS_REGION" \
            --profile "$AWS_PROFILE" 2>/dev/null || true
        
        print_status "Waiting for infrastructure stack deletion..."
        aws cloudformation wait stack-delete-complete \
            --stack-name "$PROJECT_NAME-$ENVIRONMENT-infrastructure" \
            --region "$AWS_REGION" \
            --profile "$AWS_PROFILE" 2>/dev/null || true
        
        print_success "All AWS resources have been deleted!"
    else
        print_status "Cleanup cancelled."
    fi
}

# Main deployment function
main() {
    echo " AWS Production Deployment for Comments System"
    echo "================================================"
    echo ""
    
    case "${1:-deploy}" in
        "deploy")
            check_prerequisites
            generate_secrets
            build_and_push_images
            deploy_infrastructure
            deploy_services
            sleep 30  # Wait for services to start
            run_migrations
            show_status
            echo ""
            print_success "Deployment completed successfully!"
            echo ""
            echo "Next steps:"
            echo "1. Run: ./deploy-aws.sh superuser  # To create admin user"
            echo "2. Configure your domain DNS to point to the Load Balancer"
            echo "3. Set up SSL certificate for HTTPS"
            ;;
        "superuser")
            create_superuser
            ;;
        "status")
            show_status
            ;;
        "cleanup")
            cleanup
            ;;
        "help")
            echo "Usage: $0 [command]"
            echo ""
            echo "Commands:"
            echo "  deploy    - Full deployment (default)"
            echo "  superuser - Create Django superuser"
            echo "  status    - Show deployment status"
            echo "  cleanup   - Delete all AWS resources"
            echo "  help      - Show this help"
            ;;
        *)
            print_error "Unknown command: $1"
            echo "Run '$0 help' for usage information."
            exit 1
            ;;
    esac
}

# Run main function
main "$@"