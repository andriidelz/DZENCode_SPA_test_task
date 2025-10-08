#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN} Starting Comment System Application...${NC}"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED} Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Stop any existing containers
echo -e "${YELLOW} Stopping existing containers...${NC}"
docker-compose down

# Build and start containers
echo -e "${YELLOW} Building and starting containers...${NC}"
docker-compose up --build -d

# Wait for services to be ready
echo -e "${YELLOW} Waiting for services to be ready...${NC}"
sleep 10

# Check if services are running
echo -e "${YELLOW} Checking service status...${NC}"
docker-compose ps

# Create superuser
echo -e "${YELLOW} Creating Django superuser...${NC}"
echo "Creating superuser (admin/admin123)..."
docker-compose exec -T backend python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('Superuser created successfully!')
else:
    print('Superuser already exists!')
EOF

echo -e "${GREEN} Application started successfully!${NC}"
echo -e "${GREEN} Services available at:${NC}"
echo -e "    Frontend: http://localhost:3000"
echo -e "    Backend API: http://localhost:8000"
echo -e "    Django Admin: http://localhost:8000/admin"
echo -e "    PostgreSQL: localhost:5432"
echo -e "    Redis: localhost:6379"
echo -e "${YELLOW} Admin credentials: admin / admin123${NC}"
echo -e "${YELLOW} To stop: ./stop.sh${NC}"
