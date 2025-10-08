#!/bin/bash

# Health Check Script for Comment System

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE} Comment System Health Check${NC}"
echo "=================================="

# Check if Docker is running
echo -e "${YELLOW} Checking Docker...${NC}"
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED} Docker is not running${NC}"
    exit 1
else
    echo -e "${GREEN} Docker is running${NC}"
fi

# Check if services are running
echo -e "${YELLOW} Checking services...${NC}"
if ! docker-compose ps | grep -q "Up"; then
    echo -e "${RED} Services are not running. Start with: ./start.sh${NC}"
    exit 1
fi

# Check individual services
services=("backend" "frontend" "db" "redis")
for service in "${services[@]}"; do
    if docker-compose ps $service | grep -q "Up"; then
        echo -e "${GREEN} $service is running${NC}"
    else
        echo -e "${RED} $service is not running${NC}"
        failed=true
    fi
done

# Check network connectivity
echo -e "${YELLOW} Checking network connectivity...${NC}"

# Check Backend
if curl -f -s http://localhost:8000/health/ > /dev/null 2>&1; then
    echo -e "${GREEN} Backend API is responding${NC}"
else
    echo -e "${RED} Backend API is not responding${NC}"
    failed=true
fi

# Check Frontend
if curl -f -s http://localhost:3000/ > /dev/null 2>&1; then
    echo -e "${GREEN} Frontend is responding${NC}"
else
    echo -e "${RED} Frontend is not responding${NC}"
    failed=true
fi

# Check Database
if docker-compose exec -T db pg_isready -U postgres > /dev/null 2>&1; then
    echo -e "${GREEN} Database is ready${NC}"
else
    echo -e "${RED} Database is not ready${NC}"
    failed=true
fi

# Check Redis
if docker-compose exec -T redis redis-cli ping | grep -q "PONG"; then
    echo -e "${GREEN} Redis is responding${NC}"
else
    echo -e "${RED} Redis is not responding${NC}"
    failed=true
fi

# API functional test
echo -e "${YELLOW} Testing API functionality...${NC}"
api_response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/comments/)
if [ "$api_response" = "200" ]; then
    echo -e "${GREEN} Comments API is working${NC}"
else
    echo -e "${RED} Comments API returned status: $api_response${NC}"
    failed=true
fi

# Django Admin test
admin_response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/admin/)
if [ "$admin_response" = "302" ] || [ "$admin_response" = "200" ]; then
    echo -e "${GREEN} Django Admin is accessible${NC}"
else
    echo -e "${RED} Django Admin returned status: $admin_response${NC}"
    failed=true
fi

echo "=================================="

if [ "$failed" = true ]; then
    echo -e "${RED} Health check failed. Some services are not working properly.${NC}"
    echo -e "${YELLOW} Try running: ./start.sh${NC}"
    exit 1
else
    echo -e "${GREEN} All systems are healthy!${NC}"
    echo -e "${BLUE} Access your application:${NC}"
    echo -e "    Frontend: http://localhost:3000"
    echo -e "    Backend: http://localhost:8000"
    echo -e "    Admin: http://localhost:8000/admin"
    exit 0
fi