# Makefile for Comment System

.PHONY: help dev prod test clean build deploy

# Colors
RED=\033[0;31m
GREEN=\033[0;32m
YELLOW=\033[1;33m
NC=\033[0m # No Color

help: ## Show this help message
	@echo '$(YELLOW)Available commands:$(NC)'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

# Development Commands
dev: ## Start development environment with Docker
	@echo '$(GREEN) Starting development environment...$(NC)'
	@docker-compose up --build -d
	@echo '$(GREEN) Development environment started!$(NC)'
	@echo '$(YELLOW) Frontend: http://localhost:3000$(NC)'
	@echo '$(YELLOW) Backend: http://localhost:8000$(NC)'

dev-logs: ## Show development logs
	@docker-compose logs -f

dev-stop: ## Stop development environment
	@echo '$(YELLOW) Stopping development environment...$(NC)'
	@docker-compose down
	@echo '$(GREEN) Development environment stopped!$(NC)'

dev-clean: ## Clean development environment (removes all data)
	@echo '$(RED) WARNING: This will remove all data!$(NC)'
	@read -p "Are you sure? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	@docker-compose down -v --remove-orphans
	@docker system prune -f
	@echo '$(GREEN) Development environment cleaned!$(NC)'

# Testing Commands
test: ## Run all tests
	@echo '$(GREEN) Running tests...$(NC)'
	@docker-compose exec backend python manage.py test
	@cd frontend && npm test

test-backend: ## Run backend tests only
	@echo '$(GREEN) Running backend tests...$(NC)'
	@docker-compose exec backend python manage.py test

test-frontend: ## Run frontend tests only
	@echo '$(GREEN) Running frontend tests...$(NC)'
	@cd frontend && npm test

test-coverage: ## Run tests with coverage
	@echo '$(GREEN) Running tests with coverage...$(NC)'
	@docker-compose exec backend coverage run --source='.' manage.py test
	@docker-compose exec backend coverage report
	@docker-compose exec backend coverage html

# Database Commands
db-migrate: ## Run database migrations
	@echo '$(GREEN) Running database migrations...$(NC)'
	@docker-compose exec backend python manage.py migrate

db-makemigrations: ## Create new migrations
	@echo '$(GREEN) Creating new migrations...$(NC)'
	@docker-compose exec backend python manage.py makemigrations

db-reset: ## Reset database (removes all data)
	@echo '$(RED) WARNING: This will remove all database data!$(NC)'
	@read -p "Are you sure? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	@docker-compose exec backend python manage.py flush --noinput
	@docker-compose exec backend python manage.py migrate
	@echo '$(GREEN) Database reset completed!$(NC)'

db-shell: ## Open database shell
	@docker-compose exec db psql -U postgres -d comments_db

db-backup: ## Create database backup
	@echo '$(GREEN) Creating database backup...$(NC)'
	@mkdir -p backups
	@docker-compose exec db pg_dump -U postgres comments_db > backups/backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo '$(GREEN) Database backup created!$(NC)'

# Build Commands
build: ## Build Docker images
	@echo '$(GREEN) Building Docker images...$(NC)'
	@docker-compose build

build-prod: ## Build production Docker images
	@echo '$(GREEN) Building production Docker images...$(NC)'
	@docker build -t comment-system-backend:prod -f backend/Dockerfile.prod backend/
	@docker build -t comment-system-frontend:prod -f frontend/Dockerfile.prod frontend/

# Production Commands
prod-deploy: ## Deploy to production
	@echo '$(GREEN) Deploying to production...$(NC)'
	@echo '$(YELLOW)Please configure your production environment first$(NC)'
	# Add your production deployment commands here

prod-logs: ## Show production logs
	@echo '$(GREEN) Showing production logs...$(NC)'
	# Add your production log commands here

# Utility Commands
shell-backend: ## Open backend shell
	@docker-compose exec backend python manage.py shell

shell-frontend: ## Open frontend shell
	@docker-compose exec frontend sh

logs-backend: ## Show backend logs
	@docker-compose logs -f backend

logs-frontend: ## Show frontend logs
	@docker-compose logs -f frontend

logs-db: ## Show database logs
	@docker-compose logs -f db

logs-redis: ## Show Redis logs
	@docker-compose logs -f redis

# Code Quality Commands
lint: ## Run code linting
	@echo '$(GREEN) Running code linting...$(NC)'
	@docker-compose exec backend flake8 .
	@cd frontend && npm run lint

format: ## Format code
	@echo '$(GREEN) Formatting code...$(NC)'
	@docker-compose exec backend black .
	@cd frontend && npm run format

# Testing Commands
check-prerequisites: ## Check system prerequisites
	@echo '$(GREEN) Checking prerequisites...$(NC)'
	@./check-prerequisites.sh

health-check: ## Run health check on running services
	@echo '$(GREEN) Running health check...$(NC)'
	@./health-check.sh

test-functionality: ## Run functional tests
	@echo '$(GREEN) Running functional tests...$(NC)'
	@./test-functionality.sh

quick-test: health-check test-functionality ## Run both health check and functional tests
	@echo '$(GREEN) Quick testing completed!$(NC)'

# Installation Commands
install: ## Install dependencies
	@echo '$(GREEN) Installing dependencies...$(NC)'
	@cd backend && pip install -r requirements.txt
	@cd frontend && npm install

install-dev: ## Install development dependencies
	@echo '$(GREEN) Installing development dependencies...$(NC)'
	@cd backend && pip install -r requirements-dev.txt
	@cd frontend && npm install --include=dev

# Security Commands
security-check: ## Run security checks
	@echo '$(GREEN) Running security checks...$(NC)'
	@docker-compose exec backend safety check
	@cd frontend && npm audit

security-fix: ## Fix security issues
	@echo '$(GREEN) Fixing security issues...$(NC)'
	@cd frontend && npm audit fix

# Monitoring Commands
status: ## Show service status
	@echo '$(GREEN) Service Status:$(NC)'
	@docker-compose ps

health: ## Check application health
	@echo '$(GREEN) Checking application health...$(NC)'
	@curl -f http://localhost:8000/health/ || echo 'Backend not healthy'
	@curl -f http://localhost:3000/ || echo 'Frontend not healthy'

# Performance Commands
load-test: ## Run load tests
	@echo '$(GREEN) Running load tests...$(NC)'
	@echo '$(YELLOW)Make sure the application is running first$(NC)'
	# Add load testing commands here (locust, k6, etc.)

benchmark: ## Run performance benchmarks
	@echo '$(GREEN) Running performance benchmarks...$(NC)'
	# Add benchmark commands here

# Documentation Commands
docs: ## Generate documentation
	@echo '$(GREEN) Generating documentation...$(NC)'
	@cd backend && python manage.py generate_swagger
	@cd frontend && npm run docs

docs-serve: ## Serve documentation
	@echo '$(GREEN) Serving documentation...$(NC)'
	@echo '$(YELLOW)Open http://localhost:8080 for documentation$(NC)'
	# Add documentation server command here
