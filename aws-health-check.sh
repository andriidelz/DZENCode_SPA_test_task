#!/bin/bash

# Quick AWS Deployment Status Check

set -e

# Configuration
PROJECT_NAME="comments-system"
ENVIRONMENT="production"
AWS_REGION="us-east-1"
AWS_PROFILE="default"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check infrastructure stack
check_infrastructure() {
    print_header "Infrastructure Status"
    
    INFRA_STATUS=$(aws cloudformation describe-stacks \
        --stack-name "$PROJECT_NAME-$ENVIRONMENT-infrastructure" \
        --query 'Stacks[0].StackStatus' \
        --output text \
        --region "$AWS_REGION" \
        --profile "$AWS_PROFILE" 2>/dev/null || echo "NOT_FOUND")
    
    case $INFRA_STATUS in
        "CREATE_COMPLETE"|"UPDATE_COMPLETE")
            print_success "Infrastructure: $INFRA_STATUS"
            
            # Get key infrastructure details
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
            
            ALB_DNS=$(aws cloudformation describe-stacks \
                --stack-name "$PROJECT_NAME-$ENVIRONMENT-infrastructure" \
                --query 'Stacks[0].Outputs[?OutputKey==`ALBDNS`].OutputValue' \
                --output text \
                --region "$AWS_REGION" \
                --profile "$AWS_PROFILE")
            
            echo "    Database: $DB_ENDPOINT"
            echo "   Redis: $REDIS_ENDPOINT"
            echo "   Load Balancer: $ALB_DNS"
            ;;
        "CREATE_IN_PROGRESS"|"UPDATE_IN_PROGRESS")
            print_warning "Infrastructure: $INFRA_STATUS"
            ;;
        "NOT_FOUND")
            print_error "Infrastructure: Stack not found"
            ;;
        *)
            print_error "Infrastructure: $INFRA_STATUS"
            ;;
    esac
    echo ""
}

# Check services stack
check_services() {
    print_header "Services Status"
    
    SERVICES_STATUS=$(aws cloudformation describe-stacks \
        --stack-name "$PROJECT_NAME-$ENVIRONMENT-services" \
        --query 'Stacks[0].StackStatus' \
        --output text \
        --region "$AWS_REGION" \
        --profile "$AWS_PROFILE" 2>/dev/null || echo "NOT_FOUND")
    
    case $SERVICES_STATUS in
        "CREATE_COMPLETE"|"UPDATE_COMPLETE")
            print_success "Services: $SERVICES_STATUS"
            
            # Get application URL
            APP_URL=$(aws cloudformation describe-stacks \
                --stack-name "$PROJECT_NAME-$ENVIRONMENT-services" \
                --query 'Stacks[0].Outputs[?OutputKey==`ApplicationURL`].OutputValue' \
                --output text \
                --region "$AWS_REGION" \
                --profile "$AWS_PROFILE")
            
            echo "   Application URL: $APP_URL"
            echo "   Admin Panel: $APP_URL/admin/"
            echo "   API Docs: $APP_URL/api/docs/"
            ;;
        "CREATE_IN_PROGRESS"|"UPDATE_IN_PROGRESS")
            print_warning "Services: $SERVICES_STATUS"
            ;;
        "NOT_FOUND")
            print_error "Services: Stack not found"
            ;;
        *)
            print_error "Services: $SERVICES_STATUS"
            ;;
    esac
    echo ""
}

# Check ECS services health
check_ecs_services() {
    print_header "ECS Services Health"
    
    CLUSTER_NAME="$PROJECT_NAME-$ENVIRONMENT-cluster"
    
    # Check backend service
    BACKEND_SERVICE=$(aws ecs describe-services \
        --cluster "$CLUSTER_NAME" \
        --services "$PROJECT_NAME-$ENVIRONMENT-backend" \
        --query 'services[0]' \
        --region "$AWS_REGION" \
        --profile "$AWS_PROFILE" 2>/dev/null || echo "null")
    
    if [ "$BACKEND_SERVICE" != "null" ]; then
        BACKEND_RUNNING=$(echo $BACKEND_SERVICE | jq -r '.runningCount')
        BACKEND_DESIRED=$(echo $BACKEND_SERVICE | jq -r '.desiredCount')
        
        if [ "$BACKEND_RUNNING" = "$BACKEND_DESIRED" ] && [ "$BACKEND_RUNNING" != "0" ]; then
            print_success "Backend Service: $BACKEND_RUNNING/$BACKEND_DESIRED tasks running"
        else
            print_warning "Backend Service: $BACKEND_RUNNING/$BACKEND_DESIRED tasks running"
        fi
    else
        print_error "Backend Service: Not found"
    fi
    
    # Check frontend service
    FRONTEND_SERVICE=$(aws ecs describe-services \
        --cluster "$CLUSTER_NAME" \
        --services "$PROJECT_NAME-$ENVIRONMENT-frontend" \
        --query 'services[0]' \
        --region "$AWS_REGION" \
        --profile "$AWS_PROFILE" 2>/dev/null || echo "null")
    
    if [ "$FRONTEND_SERVICE" != "null" ]; then
        FRONTEND_RUNNING=$(echo $FRONTEND_SERVICE | jq -r '.runningCount')
        FRONTEND_DESIRED=$(echo $FRONTEND_SERVICE | jq -r '.desiredCount')
        
        if [ "$FRONTEND_RUNNING" = "$FRONTEND_DESIRED" ] && [ "$FRONTEND_RUNNING" != "0" ]; then
            print_success "Frontend Service: $FRONTEND_RUNNING/$FRONTEND_DESIRED tasks running"
        else
            print_warning "Frontend Service: $FRONTEND_RUNNING/$FRONTEND_DESIRED tasks running"
        fi
    else
        print_error "Frontend Service: Not found"
    fi
    echo ""
}

# Test application health
test_application() {
    print_header "Application Health Check"
    
    # Get application URL
    APP_URL=$(aws cloudformation describe-stacks \
        --stack-name "$PROJECT_NAME-$ENVIRONMENT-services" \
        --query 'Stacks[0].Outputs[?OutputKey==`ApplicationURL`].OutputValue' \
        --output text \
        --region "$AWS_REGION" \
        --profile "$AWS_PROFILE" 2>/dev/null || echo "")
    
    if [ "$APP_URL" != "" ]; then
        # Test frontend
        if curl -s --max-time 10 "$APP_URL" > /dev/null; then
            print_success "Frontend is responding"
        else
            print_error "Frontend is not responding"
        fi
        
        # Test backend API
        if curl -s --max-time 10 "$APP_URL/api/health/" > /dev/null; then
            print_success "Backend API is responding"
        else
            print_error "Backend API is not responding"
        fi
        
        # Test admin panel
        if curl -s --max-time 10 "$APP_URL/admin/" > /dev/null; then
            print_success "Admin panel is accessible"
        else
            print_error "Admin panel is not accessible"
        fi
    else
        print_error "Application URL not found"
    fi
    echo ""
}

# Show recent logs
show_recent_logs() {
    print_header "Recent Logs (Last 5 minutes)"
    
    echo "Backend Logs:"
    aws logs filter-log-events \
        --log-group-name "/ecs/$PROJECT_NAME-$ENVIRONMENT-backend" \
        --start-time $(date -d '5 minutes ago' +%s)000 \
        --query 'events[?level==`ERROR` || level==`WARNING`].[timestamp,message]' \
        --output table \
        --region "$AWS_REGION" \
        --profile "$AWS_PROFILE" 2>/dev/null || echo "  No logs found or log group doesn't exist"
    
    echo ""
    echo "Frontend Logs:"
    aws logs filter-log-events \
        --log-group-name "/ecs/$PROJECT_NAME-$ENVIRONMENT-frontend" \
        --start-time $(date -d '5 minutes ago' +%s)000 \
        --query 'events[?level==`ERROR` || level==`WARNING`].[timestamp,message]' \
        --output table \
        --region "$AWS_REGION" \
        --profile "$AWS_PROFILE" 2>/dev/null || echo "  No logs found or log group doesn't exist"
    echo ""
}

# Main function
main() {
    echo " AWS Deployment Health Check"
    echo "=============================="
    echo ""
    
    # Check if jq is installed
    if ! command -v jq &> /dev/null; then
        print_warning "jq not found. Installing jq for JSON parsing..."
        sudo apt-get update && sudo apt-get install -y jq 2>/dev/null || {
            print_error "Could not install jq. Some features may not work properly."
        }
    fi
    
    check_infrastructure
    check_services
    check_ecs_services
    test_application
    
    if [ "${1:-}" = "--logs" ]; then
        show_recent_logs
    fi
    
    echo " Tips:"
    echo "  • Run with --logs to see recent error logs"
    echo "  • Use './deploy-aws.sh status' for detailed CloudFormation status"
    echo "  • Monitor costs in AWS Cost Explorer"
    echo ""
}

main "$@"