#!/bin/bash

# Load Testing Script for Comment System

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}⚡ Comment System Load Testing${NC}"

# Check if application is running
if ! curl -f http://localhost:8000/health/ > /dev/null 2>&1; then
    echo -e "${RED} Backend is not running. Please start the application first.${NC}"
    exit 1
fi

if ! curl -f http://localhost:3000/ > /dev/null 2>&1; then
    echo -e "${RED} Frontend is not running. Please start the application first.${NC}"
    exit 1
fi

# Install dependencies if needed
if ! command -v artillery &> /dev/null; then
    echo -e "${YELLOW} Installing Artillery for load testing...${NC}"
    npm install -g artillery
fi

# Create test data
echo -e "${YELLOW} Creating test data...${NC}"
python3 << EOF
import requests
import json

# Create test comments
for i in range(10):
    data = {
        'content': f'Test comment {i+1} for load testing',
        'author_name': f'TestUser{i+1}',
        'author_email': f'test{i+1}@example.com'
    }
    try:
        response = requests.post('http://localhost:8000/api/comments/', json=data)
        if response.status_code == 201:
            print(f'Created test comment {i+1}')
    except Exception as e:
        print(f'Error creating comment {i+1}: {e}')
EOF

# Run load tests
echo -e "${YELLOW}⚡ Running load tests...${NC}"

# Test 1: Basic API load test
echo -e "${YELLOW} Test 1: API Load Test (100 users, 30 seconds)${NC}"
artillery quick --count 100 --num 10 http://localhost:8000/api/comments/

# Test 2: Frontend load test
echo -e "${YELLOW} Test 2: Frontend Load Test (50 users, 30 seconds)${NC}"
artillery quick --count 50 --num 5 http://localhost:3000/

# Test 3: Mixed load test with custom scenario
echo -e "${YELLOW} Test 3: Mixed Scenario Load Test${NC}"
cat > load-test-config.yml << 'YAML'
config:
  target: 'http://localhost:8000'
  phases:
    - duration: 60
      arrivalRate: 10
      name: "Warm up"
    - duration: 120
      arrivalRate: 50
      name: "High load"
    - duration: 60
      arrivalRate: 20
      name: "Cool down"
  processor: "./load-test-functions.js"

scenarios:
  - name: "API Operations"
    weight: 70
    flow:
      - get:
          url: "/api/comments/"
      - think: 2
      - post:
          url: "/api/comments/"
          json:
            content: "Load test comment from {{ $randomString() }}"
            author_name: "LoadTestUser{{ $randomInt(1, 1000) }}"
            author_email: "test{{ $randomInt(1, 1000) }}@example.com"
      - think: 1
      - get:
          url: "/api/comments/"

  - name: "Frontend Access"
    weight: 30
    flow:
      - get:
          url: "http://localhost:3000/"
      - think: 5
YAML

# Create load test functions
cat > load-test-functions.js << 'JS'
module.exports = {
  generateRandomComment: function(requestParams, context, ee, next) {
    context.vars.randomComment = `Load test comment ${Math.random().toString(36).substring(7)}`;
    context.vars.randomUser = `User${Math.floor(Math.random() * 1000)}`;
    return next();
  }
};
JS

artillery run load-test-config.yml

# Cleanup
rm -f load-test-config.yml load-test-functions.js

echo -e "${GREEN} Load testing completed!${NC}"
echo -e "${YELLOW} Check the results above for performance metrics${NC}"
echo -e "${YELLOW} For detailed monitoring, check Grafana at http://localhost:3001${NC}"
