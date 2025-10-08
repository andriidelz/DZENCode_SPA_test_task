# Production Deployment Guide

## Cloud Deployment Options

### 1. AWS Deployment

#### ECS + RDS + ElastiCache

**Infrastructure Setup:**

1. **RDS PostgreSQL Instance**

```bash
# Create RDS instance
aws rds create-db-instance \
    --db-instance-identifier comment-system-db \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --master-username postgres \
    --master-user-password <secure-password> \
    --allocated-storage 20 \
    --vpc-security-group-ids sg-xxxxxxxxx
```

2.**ElastiCache Redis Cluster**

```bash
# Create Redis cluster
aws elasticache create-cache-cluster \
    --cache-cluster-id comment-system-redis \
    --cache-node-type cache.t3.micro \
    --engine redis \
    --num-cache-nodes 1
```

3.**ECS Service Deployment**

Create `ecs-task-definition.json`:

```json
{
  "family": "comment-system",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "backend",
      "image": "your-account.dkr.ecr.region.amazonaws.com/comment-system-backend:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "DEBUG", "value": "0"},
        {"name": "DB_HOST", "value": "your-rds-endpoint"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/comment-system",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

**Deployment Commands:**

```bash
# Build and push Docker images
docker build -t comment-system-backend ./backend
docker tag comment-system-backend:latest $AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/comment-system-backend:latest
docker push $AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/comment-system-backend:latest

# Register task definition
aws ecs register-task-definition --cli-input-json file://ecs-task-definition.json

# Create service
aws ecs create-service \
    --cluster comment-system-cluster \
    --service-name comment-system-service \
    --task-definition comment-system \
    --desired-count 2 \
    --launch-type FARGATE
```

### 2. Google Cloud Platform (GCP)

#### Cloud Run + Cloud SQL + Memorystore

**Setup Commands:**

```bash
# Enable required APIs
gcloud services enable run.googleapis.com sql-component.googleapis.com redis.googleapis.com

# Create Cloud SQL instance
gcloud sql instances create comment-system-db \
    --database-version=POSTGRES_14 \
    --tier=db-f1-micro \
    --region=us-central1

# Create database
gcloud sql databases create comments_db --instance=comment-system-db

# Create Redis instance
gcloud redis instances create comment-system-redis \
    --size=1 \
    --region=us-central1 \
    --redis-version=redis_6_x

# Build and deploy to Cloud Run
gcloud builds submit --tag gcr.io/$PROJECT_ID/comment-system-backend ./backend
gcloud run deploy comment-system-backend \
    --image gcr.io/$PROJECT_ID/comment-system-backend \
    --platform managed \
    --region us-central1 \
    --set-env-vars="DB_HOST=<cloud-sql-ip>,REDIS_URL=redis://<redis-ip>:6379"
```

### 3. Azure Deployment

#### Container Instances + PostgreSQL + Redis Cache

```bash
# Create resource group
az group create --name CommentSystemRG --location eastus

# Create PostgreSQL server
az postgres server create \
    --resource-group CommentSystemRG \
    --name comment-system-postgres \
    --location eastus \
    --admin-user postgres \
    --admin-password <secure-password> \
    --sku-name GP_Gen5_2

# Create Redis Cache
az redis create \
    --resource-group CommentSystemRG \
    --name comment-system-redis \
    --location eastus \
    --sku Basic \
    --vm-size c0

# Deploy container
az container create \
    --resource-group CommentSystemRG \
    --name comment-system-backend \
    --image your-registry/comment-system-backend:latest \
    --ports 8000 \
    --environment-variables \
        DB_HOST=comment-system-postgres.postgres.database.azure.com \
        REDIS_URL=redis://comment-system-redis.redis.cache.windows.net:6380
```

## Kubernetes Deployment

### 1. Create Kubernetes Manifests

**namespace.yaml:**

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: comment-system
```

**configmap.yaml:**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: comment-system-config
  namespace: comment-system
data:
  DEBUG: "0"
  ALLOWED_HOSTS: "yourdomain.com,www.yourdomain.com"
  DB_HOST: "postgres-service"
  REDIS_URL: "redis://redis-service:6379/0"
```

**postgres-deployment.yaml:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres
  namespace: comment-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15-alpine
        env:
        - name: POSTGRES_DB
          value: "comments_db"
        - name: POSTGRES_USER
          value: "postgres"
        - name: POSTGRES_PASSWORD
          value: "postgres123"
        ports:
        - containerPort: 5432
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
      volumes:
      - name: postgres-storage
        persistentVolumeClaim:
          claimName: postgres-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: postgres-service
  namespace: comment-system
spec:
  selector:
    app: postgres
  ports:
  - port: 5432
    targetPort: 5432
```

**backend-deployment.yaml:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: comment-system
spec:
  replicas: 3
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: backend
        image: your-registry/comment-system-backend:latest
        envFrom:
        - configMapRef:
            name: comment-system-config
        ports:
        - containerPort: 8000
        livenessProbe:
          httpGet:
            path: /health/
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: backend-service
  namespace: comment-system
spec:
  selector:
    app: backend
  ports:
  - port: 8000
    targetPort: 8000
  type: LoadBalancer
```

### 2. Deploy to Kubernetes

```bash
# Apply manifests
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f postgres-deployment.yaml
kubectl apply -f backend-deployment.yaml

# Check deployment status
kubectl get pods -n comment-system
kubectl get services -n comment-system

# View logs
kubectl logs -l app=backend -n comment-system
```

## CI/CD Pipeline

### GitHub Actions Workflow

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy Comment System

on:
  push:
    branches: [ main ]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
    - name: Checkout repository
      uses: actions/checkout@v3

    - name: Log in to Container Registry
      uses: docker/login-action@v2
      with:
        registry: ${{ env.REGISTRY }}
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}

    - name: Build and push Backend image
      uses: docker/build-push-action@v4
      with:
        context: ./backend
        push: true
        tags: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}-backend:latest

    - name: Build and push Frontend image
      uses: docker/build-push-action@v4
      with:
        context: ./frontend
        push: true
        tags: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}-frontend:latest

    - name: Deploy to production
      run: |
        # Add your deployment commands here
        echo "Deploying to production..."
```

## Security Configuration

### 1. SSL/TLS Setup

```bash
# Using Let's Encrypt with Nginx
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

### 2. Environment Security

- Use AWS Secrets Manager / Azure Key Vault / GCP Secret Manager
- Never commit `.env` files to git
- Rotate secrets regularly
- Use IAM roles instead of API keys when possible

### 3. Database Security

- Enable SSL connections
- Use read replicas for scaling
- Regular backups
- Network isolation (VPC/private subnets)

## Monitoring and Logging

### 1. Application Monitoring

```python
# Add to Django settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/var/log/django/comment-system.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

### 2. Performance Monitoring

- Use Sentry for error tracking
- Implement Prometheus metrics
- Set up Grafana dashboards
- Monitor database performance

## Scaling Considerations

### 1. Horizontal Scaling

- Load balancer configuration
- Database read replicas
- Redis clustering
- CDN for static files

### 2. Performance Optimization

- Database indexing
- Query optimization
- Caching strategies
- Background task processing

## Backup Strategy

### 1. Database Backups

```bash
# Automated PostgreSQL backup
pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore from backup
psql -h $DB_HOST -U $DB_USER -d $DB_NAME < backup_file.sql
```

### 2. Media Files Backup

- Use cloud storage (S3, GCS, Azure Blob)
- Regular sync to backup storage
- Version control for critical files
