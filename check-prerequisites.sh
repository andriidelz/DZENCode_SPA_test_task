#!/bin/bash

# Prerequisites Check Script

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE} Comment System Prerequisites Check${NC}"
echo "======================================"

# Check functions
check_command() {
    if command -v $1 &> /dev/null; then
        echo -e "${GREEN} $1 is installed${NC}"
        return 0
    else
        echo -e "${RED} $1 is not installed${NC}"
        return 1
    fi
}

check_port() {
    if netstat -tuln 2>/dev/null | grep -q ":$1 "; then
        echo -e "${RED} Port $1 is already in use${NC}"
        echo -e "${YELLOW}   Process using port $1:${NC}"
        lsof -i :$1 2>/dev/null || echo "   Unable to identify process"
        return 1
    else
        echo -e "${GREEN} Port $1 is available${NC}"
        return 0
    fi
}

failed=false

# Check Docker
echo -e "${YELLOW}Checking Docker...${NC}"
if check_command docker; then
    docker_version=$(docker --version)
    echo -e "${BLUE}   Version: $docker_version${NC}"
    
    # Check if Docker daemon is running
    if docker info &> /dev/null; then
        echo -e "${GREEN} Docker daemon is running${NC}"
    else
        echo -e "${RED} Docker daemon is not running${NC}"
        echo -e "${YELLOW}   Try: sudo systemctl start docker${NC}"
        failed=true
    fi
else
    echo -e "${YELLOW}   Install: https://docs.docker.com/get-docker/${NC}"
    failed=true
fi
echo ""

# Check Docker Compose
echo -e "${YELLOW}Checking Docker Compose...${NC}"
if check_command docker-compose; then
    compose_version=$(docker-compose --version)
    echo -e "${BLUE}   Version: $compose_version${NC}"
else
    echo -e "${YELLOW}   Install: https://docs.docker.com/compose/install/${NC}"
    failed=true
fi
echo ""

# Check Git
echo -e "${YELLOW}Checking Git...${NC}"
if check_command git; then
    git_version=$(git --version)
    echo -e "${BLUE}   Version: $git_version${NC}"
else
    echo -e "${YELLOW}   Install: sudo apt install git (Ubuntu) or brew install git (macOS)${NC}"
    failed=true
fi
echo ""

# Check curl (for testing)
echo -e "${YELLOW}Checking curl...${NC}"
if check_command curl; then
    curl_version=$(curl --version | head -n1)
    echo -e "${BLUE}   Version: $curl_version${NC}"
else
    echo -e "${YELLOW}   Install: sudo apt install curl (Ubuntu) or brew install curl (macOS)${NC}"
    failed=true
fi
echo ""

# Check required ports
echo -e "${YELLOW}Checking required ports...${NC}"
ports=(3000 8000 5432 6379)
for port in "${ports[@]}"; do
    if ! check_port $port; then
        failed=true
    fi
done
echo ""

# Check disk space
echo -e "${YELLOW}Checking disk space...${NC}"
available_space=$(df -h . | awk 'NR==2 {print $4}' | sed 's/[^0-9.]//g')
if [ $(echo "$available_space > 2" | bc -l 2>/dev/null || echo "1") -eq 1 ]; then
    echo -e "${GREEN} Sufficient disk space available${NC}"
else
    echo -e "${RED} Low disk space (less than 2GB available)${NC}"
    failed=true
fi
echo ""

# Check memory
echo -e "${YELLOW}Checking available memory...${NC}"
if command -v free &> /dev/null; then
    available_mem=$(free -m | awk 'NR==2{printf "%.1f", $7/1024}')
    echo -e "${BLUE}   Available memory: ${available_mem}GB${NC}"
    if [ $(echo "$available_mem > 1" | bc -l 2>/dev/null || echo "1") -eq 1 ]; then
        echo -e "${GREEN} Sufficient memory available${NC}"
    else
        echo -e "${YELLOW}  Low memory (less than 1GB available)${NC}"
    fi
else
    echo -e "${YELLOW}  Unable to check memory${NC}"
fi
echo ""

# Check required files
echo -e "${YELLOW}Checking project files...${NC}"
required_files=(
    "docker-compose.yml"
    "backend/Dockerfile"
    "frontend/Dockerfile"
    "backend/requirements.txt"
    "frontend/package.json"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN} $file exists${NC}"
    else
        echo -e "${RED} $file is missing${NC}"
        failed=true
    fi
done
echo ""

# Summary
echo "======================================"
if [ "$failed" = true ]; then
    echo -e "${RED} Prerequisites check failed${NC}"
    echo -e "${YELLOW}Please resolve the issues above before proceeding.${NC}"
    echo ""
    echo -e "${BLUE} Common solutions:${NC}"
    echo -e "   • Install Docker: https://docs.docker.com/get-docker/"
    echo -e "   • Start Docker: sudo systemctl start docker"
    echo -e "   • Free up ports: sudo lsof -i :PORT_NUMBER"
    echo -e "   • Free up disk space: docker system prune"
    exit 1
else
    echo -e "${GREEN} All prerequisites are met!${NC}"
    echo -e "${BLUE}You're ready to start the application.${NC}"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo -e "   1. Run: ./start.sh"
    echo -e "   2. Wait for services to start"
    echo -e "   3. Run: ./health-check.sh"
    echo -e "   4. Run: ./test-functionality.sh"
    exit 0
fi