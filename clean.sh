#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${RED}  WARNING: This will remove all data including database!${NC}"
read -p "Are you sure? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}🧹 Cleaning up...${NC}"
    
    # Stop and remove containers, networks, volumes
    docker-compose down -v --remove-orphans
    
    # Remove images
    docker-compose down --rmi all
    
    # Prune unused volumes
    docker volume prune -f
    
    echo -e "${GREEN} Cleanup completed!${NC}"
else
    echo -e "${GREEN} Cleanup cancelled.${NC}"
fi
