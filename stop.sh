#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW} Stopping Comment System Application...${NC}"

# Stop all containers
docker-compose down

echo -e "${GREEN} Application stopped successfully!${NC}"
echo -e "${YELLOW} To start again: ./start.sh${NC}"
echo -e "${YELLOW} To clean all data: ./clean.sh${NC}"
