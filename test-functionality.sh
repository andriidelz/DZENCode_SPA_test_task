#!/bin/bash

# Quick Functional Test for Comment System

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧪 Comment System Functional Tests${NC}"
echo "==================================="

# Test counter
passed=0
failed=0

# Function to run test
run_test() {
    local test_name="$1"
    local test_command="$2"
    local expected_pattern="$3"
    
    echo -e "${YELLOW}Testing: $test_name${NC}"
    
    result=$(eval "$test_command" 2>&1)
    
    if echo "$result" | grep -q "$expected_pattern"; then
        echo -e "${GREEN} PASSED: $test_name${NC}"
        ((passed++))
    else
        echo -e "${RED} FAILED: $test_name${NC}"
        echo -e "${RED}   Output: $result${NC}"
        ((failed++))
    fi
    echo ""
}

# 1. Test Backend Health
run_test "Backend Health Check" \
    "curl -s http://localhost:8000/health/" \
    "OK"

# 2. Test API Root
run_test "API Root Endpoint" \
    "curl -s http://localhost:8000/api/" \
    "comments"

# 3. Test Comments List (Empty or with data)
run_test "Comments List API" \
    "curl -s http://localhost:8000/api/comments/" \
    '\[\]|\[.*\]'

# 4. Test Creating Comment
echo -e "${YELLOW}Testing: Create Comment via API${NC}"
create_response=$(curl -s -X POST http://localhost:8000/api/comments/ \
    -H "Content-Type: application/json" \
    -d '{
        "content": "Test comment from automated test",
        "author_name": "Test User",
        "author_email": "test@example.com"
    }')

if echo "$create_response" | grep -q "Test comment from automated test"; then
    echo -e "${GREEN} PASSED: Create Comment via API${NC}"
    ((passed++))
    comment_id=$(echo "$create_response" | grep -o '"id":[0-9]*' | cut -d: -f2)
    echo -e "${BLUE}   Created comment with ID: $comment_id${NC}"
else
    echo -e "${RED} FAILED: Create Comment via API${NC}"
    echo -e "${RED}   Response: $create_response${NC}"
    ((failed++))
fi
echo ""

# 5. Test Frontend Accessibility
run_test "Frontend Accessibility" \
    "curl -s http://localhost:3000/" \
    "<title>|<html>|<!DOCTYPE"

# 6. Test Django Admin
run_test "Django Admin Accessibility" \
    "curl -s http://localhost:8000/admin/" \
    "Django administration|login"

# 7. Test API with Created Comment
if [ ! -z "$comment_id" ]; then
    run_test "Retrieve Created Comment" \
        "curl -s http://localhost:8000/api/comments/$comment_id/" \
        "Test comment from automated test"
fi

# 8. Test CORS Headers
echo -e "${YELLOW}Testing: CORS Headers${NC}"
cors_response=$(curl -s -I -H "Origin: http://localhost:3000" http://localhost:8000/api/comments/)
if echo "$cors_response" | grep -q "Access-Control-Allow-Origin"; then
    echo -e "${GREEN} PASSED: CORS Headers${NC}"
    ((passed++))
else
    echo -e "${RED} FAILED: CORS Headers${NC}"
    ((failed++))
fi
echo ""

# 9. Test Static Files
run_test "Static Files Access" \
    "curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/static/" \
    "200|403"

# 10. Database Connection Test
echo -e "${YELLOW}Testing: Database Connection${NC}"
db_test=$(docker-compose exec -T backend python manage.py shell -c "
from django.db import connection
cursor = connection.cursor()
cursor.execute('SELECT 1')
print('DB_OK')
" 2>/dev/null)

if echo "$db_test" | grep -q "DB_OK"; then
    echo -e "${GREEN} PASSED: Database Connection${NC}"
    ((passed++))
else
    echo -e "${RED} FAILED: Database Connection${NC}"
    ((failed++))
fi
echo ""

# 11. Redis Connection Test
echo -e "${YELLOW}Testing: Redis Connection${NC}"
redis_test=$(docker-compose exec -T backend python -c "
import redis
import os
redis_url = os.environ.get('REDIS_URL', 'redis://redis:6379/0')
r = redis.from_url(redis_url)
r.set('test_key', 'test_value')
result = r.get('test_key')
print('REDIS_OK' if result else 'REDIS_FAIL')
" 2>/dev/null)

if echo "$redis_test" | grep -q "REDIS_OK"; then
    echo -e "${GREEN} PASSED: Redis Connection${NC}"
    ((passed++))
else
    echo -e "${RED} FAILED: Redis Connection${NC}"
    ((failed++))
fi
echo ""

# Summary
echo "==================================="
echo -e "${BLUE} Test Results Summary${NC}"
echo -e "${GREEN} Passed: $passed${NC}"
echo -e "${RED} Failed: $failed${NC}"

total=$((passed + failed))
if [ $total -eq 0 ]; then
    echo -e "${YELLOW} No tests were run${NC}"
    exit 1
fi

success_rate=$((passed * 100 / total))
echo -e "${BLUE} Success Rate: $success_rate%${NC}"

if [ $failed -eq 0 ]; then
    echo -e "${GREEN} All tests passed! Your application is working correctly.${NC}"
    echo ""
    echo -e "${BLUE} Ready for production deployment!${NC}"
    echo -e "${YELLOW} Next step: Run production deployment${NC}"
    exit 0
else
    echo -e "${RED} Some tests failed. Please check the issues above.${NC}"
    echo ""
    echo -e "${YELLOW} Troubleshooting tips:${NC}"
    echo -e "   1. Check service logs: docker-compose logs"
    echo -e "   2. Restart services: ./stop.sh && ./start.sh"
    echo -e "   3. Check health: ./health-check.sh"
    exit 1
fi