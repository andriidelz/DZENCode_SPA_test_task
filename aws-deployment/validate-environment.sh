#!/bin/bash

# AWS Deployment Environment Validator
# Validates AWS environment before deployment

set -e

# Configuration
PROJECT_NAME="comments-system"
ENVIRONMENT="production"
AWS_REGION="us-east-1"
AWS_PROFILE="default"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Counters
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNING_CHECKS=0

print_header() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

print_check() {
    echo -n "  Checking $1... "
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
}

print_pass() {
    echo -e "${GREEN}✓ PASS${NC}"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
}

print_fail() {
    echo -e "${RED}✗ FAIL${NC} - $1"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
}

print_warn() {
    echo -e "${YELLOW}⚠ WARNING${NC} - $1"
    WARNING_CHECKS=$((WARNING_CHECKS + 1))
}

# Check AWS CLI
check_aws_cli() {
    print_header "AWS CLI Validation"
    
    print_check "AWS CLI installation"
    if command -v aws &> /dev/null; then
        AWS_VERSION=$(aws --version 2>&1 | cut -d' ' -f1 | cut -d'/' -f2)
        print_pass
        echo "    Version: $AWS_VERSION"
    else
        print_fail "AWS CLI not installed"
        return 1
    fi
    
    print_check "AWS credentials"
    if aws sts get-caller-identity --profile "$AWS_PROFILE" &> /dev/null; then
        ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text --profile "$AWS_PROFILE")
        USER_ARN=$(aws sts get-caller-identity --query Arn --output text --profile "$AWS_PROFILE")
        print_pass
        echo "    Account ID: $ACCOUNT_ID"
        echo "    User/Role: $USER_ARN"
    else
        print_fail "AWS credentials not configured or invalid"
        return 1
    fi
    
    print_check "AWS region"
    CONFIGURED_REGION=$(aws configure get region --profile "$AWS_PROFILE" 2>/dev/null || echo "not-set")
    if [ "$CONFIGURED_REGION" = "$AWS_REGION" ] || [ "$CONFIGURED_REGION" = "not-set" ]; then
        print_pass
        echo "    Using region: $AWS_REGION"
    else
        print_warn "Configured region ($CONFIGURED_REGION) differs from target region ($AWS_REGION)"
    fi
}

# Check IAM permissions
check_iam_permissions() {
    print_header "IAM Permissions Validation"
    
    # List of required permissions to check
    declare -a SERVICES=("ecs" "rds" "elasticache" "ec2" "iam" "logs" "s3" "elasticloadbalancing" "cloudformation" "ecr")
    
    for service in "${SERVICES[@]}"; do
        print_check "$service permissions"
        case $service in
            "ecs")
                if aws ecs list-clusters --region "$AWS_REGION" --profile "$AWS_PROFILE" &> /dev/null; then
                    print_pass
                else
                    print_fail "No ECS permissions"
                fi
                ;;
            "rds")
                if aws rds describe-db-instances --region "$AWS_REGION" --profile "$AWS_PROFILE" &> /dev/null; then
                    print_pass
                else
                    print_fail "No RDS permissions"
                fi
                ;;
            "ec2")
                if aws ec2 describe-vpcs --region "$AWS_REGION" --profile "$AWS_PROFILE" &> /dev/null; then
                    print_pass
                else
                    print_fail "No EC2 permissions"
                fi
                ;;
            "cloudformation")
                if aws cloudformation list-stacks --region "$AWS_REGION" --profile "$AWS_PROFILE" &> /dev/null; then
                    print_pass
                else
                    print_fail "No CloudFormation permissions"
                fi
                ;;
            *)
                # Basic check for other services
                if aws $service help &> /dev/null; then
                    print_pass
                else
                    print_warn "Cannot verify $service permissions"
                fi
                ;;
        esac
    done
}

# Check service quotas
check_service_quotas() {
    print_header "Service Quotas Validation"
    
    print_check "VPC limit"
    VPC_COUNT=$(aws ec2 describe-vpcs --region "$AWS_REGION" --profile "$AWS_PROFILE" --query 'length(Vpcs)' --output text 2>/dev/null || echo "0")
    if [ "$VPC_COUNT" -lt 5 ]; then  # Default VPC limit is 5
        print_pass
        echo "    Current VPCs: $VPC_COUNT/5"
    else
        print_warn "VPC limit may be reached ($VPC_COUNT/5)"
    fi
    
    print_check "ECS cluster limit"
    ECS_CLUSTERS=$(aws ecs list-clusters --region "$AWS_REGION" --profile "$AWS_PROFILE" --query 'length(clusterArns)' --output text 2>/dev/null || echo "0")
    if [ "$ECS_CLUSTERS" -lt 10 ]; then  # Default cluster limit is 10
        print_pass
        echo "    Current clusters: $ECS_CLUSTERS/10"
    else
        print_warn "ECS cluster limit may be reached ($ECS_CLUSTERS/10)"
    fi
    
    print_check "RDS instance limit"
    RDS_INSTANCES=$(aws rds describe-db-instances --region "$AWS_REGION" --profile "$AWS_PROFILE" --query 'length(DBInstances)' --output text 2>/dev/null || echo "0")
    if [ "$RDS_INSTANCES" -lt 20 ]; then  # Default RDS limit is 20
        print_pass
        echo "    Current instances: $RDS_INSTANCES/20"
    else
        print_warn "RDS instance limit may be reached ($RDS_INSTANCES/20)"
    fi
}

# Check existing resources
check_existing_resources() {
    print_header "Existing Resources Check"
    
    print_check "Existing CloudFormation stacks"
    EXISTING_STACKS=$(aws cloudformation list-stacks \
        --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE \
        --query "StackSummaries[?contains(StackName,'$PROJECT_NAME')].StackName" \
        --output text \
        --region "$AWS_REGION" \
        --profile "$AWS_PROFILE" 2>/dev/null || echo "")
    
    if [ -z "$EXISTING_STACKS" ]; then
        print_pass
        echo "    No existing stacks found"
    else
        print_warn "Existing stacks found: $EXISTING_STACKS"
        echo "    These may be overwritten during deployment"
    fi
    
    print_check "ECR repositories"
    BACKEND_REPO=$(aws ecr describe-repositories \
        --repository-names "$PROJECT_NAME/backend" \
        --region "$AWS_REGION" \
        --profile "$AWS_PROFILE" 2>/dev/null && echo "exists" || echo "not-found")
    FRONTEND_REPO=$(aws ecr describe-repositories \
        --repository-names "$PROJECT_NAME/frontend" \
        --region "$AWS_REGION" \
        --profile "$AWS_PROFILE" 2>/dev/null && echo "exists" || echo "not-found")
    
    if [ "$BACKEND_REPO" = "not-found" ] && [ "$FRONTEND_REPO" = "not-found" ]; then
        print_pass
        echo "    ECR repositories will be created"
    else
        print_warn "ECR repositories may already exist"
    fi
}

# Check local environment
check_local_environment() {
    print_header "Local Environment Validation"
    
    print_check "Docker installation"
    if command -v docker &> /dev/null; then
        DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | cut -d',' -f1)
        print_pass
        echo "    Version: $DOCKER_VERSION"
    else
        print_fail "Docker not installed"
    fi
    
    print_check "Docker daemon"
    if docker info &> /dev/null; then
        print_pass
    else
        print_fail "Docker daemon not running"
    fi
    
    print_check "Python installation"
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        print_pass
        echo "    Version: $PYTHON_VERSION"
    else
        print_fail "Python 3 not installed"
    fi
    
    print_check "Project files"
    if [ -f "deploy-aws.sh" ] && [ -f "aws-deployment/cloudformation-template.yml" ]; then
        print_pass
    else
        print_fail "Required project files not found"
    fi
}

# Check cost implications
check_cost_implications() {
    print_header "Cost Implications"
    
    echo "  Estimated monthly costs:"
    echo "    • ECS Fargate (2 tasks):     ~\$35-50"
    echo "    • RDS PostgreSQL (t3.micro): ~\$15-20"
    echo "    • ElastiCache Redis:         ~\$15-20"
    echo "    • Application Load Balancer: ~\$20-25"
    echo "    • Data transfer & storage:   ~\$5-10"
    echo "    • CloudWatch logs:           ~\$5-10"
    echo "    ----------------------------------------"
    echo "    • Total estimated:           ~\$95-135/month"
    echo ""
    
    print_check "Billing alerts configured"
    BILLING_ALARMS=$(aws cloudwatch describe-alarms \
        --alarm-name-prefix "billing" \
        --region us-east-1 \
        --profile "$AWS_PROFILE" \
        --query 'length(MetricAlarms)' \
        --output text 2>/dev/null || echo "0")
    
    if [ "$BILLING_ALARMS" -gt 0 ]; then
        print_pass
        echo "    Found $BILLING_ALARMS billing alarms"
    else
        print_warn "No billing alerts configured"
        echo "    Consider setting up billing alerts in CloudWatch"
    fi
}

# Generate summary report
generate_summary() {
    echo ""
    print_header "Validation Summary"
    echo "  Total checks: $TOTAL_CHECKS"
    echo -e "  ${GREEN}Passed: $PASSED_CHECKS${NC}"
    echo -e "  ${YELLOW}Warnings: $WARNING_CHECKS${NC}"
    echo -e "  ${RED}Failed: $FAILED_CHECKS${NC}"
    echo ""
    
    if [ "$FAILED_CHECKS" -eq 0 ]; then
        echo -e "${GREEN} Environment is ready for deployment!${NC}"
        echo ""
        echo "Next steps:"
        echo "  1. Run: ./deploy-aws.sh"
        echo "  2. Or: make deploy"
        echo ""
        if [ "$WARNING_CHECKS" -gt 0 ]; then
            echo -e "${YELLOW}  Please review warnings above before proceeding.${NC}"
        fi
    else
        echo -e "${RED} Environment validation failed!${NC}"
        echo ""
        echo "Please fix the failed checks before deployment."
        echo "Refer to AWS_DEPLOYMENT.md for troubleshooting help."
        exit 1
    fi
}

# Main function
main() {
    echo " AWS Deployment Environment Validator"
    echo "======================================="
    echo ""
    echo "Project: $PROJECT_NAME"
    echo "Environment: $ENVIRONMENT"
    echo "Region: $AWS_REGION"
    echo "Profile: $AWS_PROFILE"
    echo ""
    
    check_local_environment
    echo ""
    check_aws_cli
    echo ""
    check_iam_permissions
    echo ""
    check_service_quotas
    echo ""
    check_existing_resources
    echo ""
    check_cost_implications
    
    generate_summary
}

main "$@"