# Django Comment System Backend

A powerful Django REST API backend for a modern comment system with user management, file uploads, and analytics.

## Features

- **Comment Management** - Full CRUD operations for comments with moderation
- **User System** - Authentication, profiles, and user behavior tracking
- **File Uploads** - Image and document uploads with thumbnails
- **Analytics** - Real-time statistics and user behavior analysis
- **Security** - Rate limiting, validation, and security headers
- **Performance** - Caching, pagination, and optimized queries
- **API First** - RESTful API with comprehensive documentation

## Tech Stack

- **Framework:** Django 4.2 + Django REST Framework
- **Database:** PostgreSQL (with SQLite fallback)
- **Cache:** Redis (with memory cache fallback)
- **Files:** PIL for image processing
- **Authentication:** Token-based authentication
- **API:** RESTful with filtering, pagination, and throttling

## Quick Start

### Prerequisites

- Python 3.9+
- PostgreSQL (optional, SQLite works for development)
- Redis (optional, memory cache works for development)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Development settings
DEBUG=True
USE_SQLITE=True
USE_MEMORY_CACHE=True

# Production settings
DEBUG=False
SECRET_KEY=your-production-secret-key
DB_NAME=comment_system
DB_USER=postgres
DB_PASSWORD=your-password
REDIS_URL=redis://localhost:6379/1
```

## API Endpoints

### Comments API

- `GET /api/comments/` - List comments with filtering
- `POST /api/comments/` - Create new comment
- `GET /api/comments/{id}/` - Get comment details
- `PUT /api/comments/{id}/` - Update comment
- `DELETE /api/comments/{id}/` - Delete comment
- `POST /api/comments/{id}/like/` - Toggle comment like
- `POST /api/comments/{id}/report/` - Report comment
- `GET /api/comments/stats/` - Comment statistics

### Users API

- `POST /api/users/register/` - User registration
- `POST /api/users/login/` - User login
- `POST /api/users/logout/` - User logout
- `GET /api/users/profile/` - Get user profile
- `PUT /api/users/profile/` - Update user profile
- `GET /api/users/activity/` - User activity history
- `GET /api/users/stats/` - User statistics

### Files API

- `GET /api/files/` - List files with filtering
- `POST /api/files/` - Upload new file
- `GET /api/files/{id}/` - Get file details
- `PUT /api/files/{id}/` - Update file metadata
- `DELETE /api/files/{id}/` - Delete file
- `GET /api/files/{id}/download/` - Download file
- `GET /api/files/{id}/thumbnail/` - Get thumbnail
- `GET /api/files/stats/` - File statistics

### Analytics API

- `POST /api/analytics/events/` - Track analytics event
- `POST /api/analytics/track/` - Simple event tracking
- `GET /api/analytics/daily-stats/` - Daily statistics
- `GET /api/analytics/popular-content/` - Popular content
- `GET /api/analytics/dashboard/` - Analytics dashboard
- `GET /api/analytics/real-time/` - Real-time statistics

## Features in Detail

### Comment System

- CRUD operations for comments
- Like/unlike functionality
- Comment reporting and moderation
- Rate limiting and spam protection
- Rich text content support
- User identification tracking

### User Management

- User registration and authentication
- Extended user profiles with avatars
- User activity tracking
- Session management
- Privacy settings
- Email notifications preferences

### File Management

- Image and document uploads
- Automatic thumbnail generation
- File type validation
- Size limits and optimization
- Download tracking
- Public/private file access

### Analytics & Insights

- Real-time event tracking
- User behavior analysis
- Content popularity metrics
- Daily statistics aggregation
- Dashboard with insights
- Growth rate calculations

### Security Features

- Rate limiting per IP
- Input validation and sanitization
- CSRF protection
- SQL injection prevention
- XSS protection
- Secure file uploads

## Database Schema

### Comments App

- `Comment` - Main comment model with content, author, timestamps
- `CommentLike` - Like/reaction tracking
- `CommentReport` - Content moderation and reporting

### Users App

- `UserProfile` - Extended user information and preferences
- `UserActivity` - User action tracking
- `UserSession` - Session management and security

### Files App

- `FileUpload` - File metadata and management
- `FileThumbnail` - Generated thumbnails for images
- `FileDownload` - Download tracking and analytics

### Analytics App

- `AnalyticsEvent` - General event tracking
- `DailyStats` - Aggregated daily statistics
- `PopularContent` - Content popularity tracking
- `UserBehavior` - User engagement and behavior patterns

## Development

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-django factory-boy coverage

# Run tests
pytest

# Run with coverage
coverage run -m pytest
coverage report
coverage html
```

### Code Quality

```bash
# Install development tools
pip install black flake8 isort

# Format code
black .
isort .

# Check code quality
flake8 .
```

### Database Management

```bash
# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Reset database (development only)
python manage.py flush

# Create test data
python manage.py shell
# Use Django shell to create test objects
```

### Background Tasks

```bash
# Install Celery for background tasks
pip install celery redis

# Start Celery worker
celery -A core worker -l info

# Start Celery beat (for scheduled tasks)
celery -A core beat -l info
```

## Production Deployment

### Environment Setup

```bash
# Production environment variables
DEBUG=False
SECRET_KEY=your-secure-secret-key
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DB_NAME=comment_system_prod
REDIS_URL=redis://redis-server:6379/0
```

### Database Setup

```sql
-- PostgreSQL setup
CREATE DATABASE comment_system_prod;
CREATE USER comment_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE comment_system_prod TO comment_user;
```

### Web Server

```bash
# Using Gunicorn
gunicorn core.wsgi:application --bind 0.0.0.0:8000

# Using uWSGI
uwsgi --http :8000 --module core.wsgi
```

### Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000"]
```

## Monitoring and Maintenance

### Health Checks

- `GET /health/` - Application health status
- Database connectivity check
- Cache availability check
- File system access check

### Logging

- Structured logging with different levels
- File-based logging for production
- Error tracking and monitoring
- Performance monitoring

### Backup Strategy

- Database backups (daily)
- Media files backup
- Configuration backup
- Migration scripts backup

## API Documentation

- **Development:** `http://localhost:8000/api/docs/`
- **Interactive API:** `http://localhost:8000/api/`
- **Admin Panel:** `http://localhost:8000/admin/`

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License.

## Support

For support and questions, please open an issue in the repository.

---

**Author:** Andrii Zaliubovskyi
**Last Updated:** October 2025
