# Local Development Setup

## Швидкий Старт з Docker (Рекомендовано)

### 1. Встановлення залежностей

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

### 2. Запуск додатку

```bash
# Клонуйте репозиторій
git clone <your-repo-url>
cd comment-system

# Зробіть скрипти виконуваними (Linux/Mac)
chmod +x start.sh stop.sh clean.sh

# Запустіть додаток
./start.sh
```

### 3. Доступ до сервісів

- **Frontend**: <http://localhost:3000>
- **Backend API**: <http://localhost:8000>
- **Django Admin**: <http://localhost:8000/admin> (admin/admin123)
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

### 4. Команди управління

```bash
# Зупинити додаток
./stop.sh

# Очистити всі дані
./clean.sh

# Переглянути логи
docker-compose logs -f

# Переглянути логи конкретного сервісу
docker-compose logs -f backend
docker-compose logs -f frontend
```

## Ручне Встановлення (Без Docker)

### Backend (Django)

#### 1. Встановлення Python залежностей

```bash
cd backend
pip install -r requirements.txt
```

#### 2. Налаштування бази даних

```bash
# Встановіть PostgreSQL
sudo apt install postgresql postgresql-contrib  # Ubuntu
brew install postgresql  # macOS

# Створіть базу даних
sudo -u postgres createdb comments_db
sudo -u postgres createuser --interactive
```

#### 3. Налаштування Redis

```bash
# Встановіть Redis
sudo apt install redis-server  # Ubuntu
brew install redis  # macOS

# Запустіть Redis
redis-server
```

#### 4. Міграції та запуск

```bash
# Скопіюйте файл середовища
cp .env.dev .env

# Виконайте міграції
python manage.py migrate

# Створіть суперкористувача
python manage.py createsuperuser

# Зберіть статичні файли
python manage.py collectstatic

# Запустіть сервер
python manage.py runserver
```

#### 5. Запустіть Celery (в окремих терміналах)

```bash
# Worker
celery -A core worker -l info

# Beat scheduler
celery -A core beat -l info
```

### Frontend (Vue.js)

#### 1. Встановлення Node.js залежностей

```bash
cd frontend
npm install
```

#### 2. Запуск dev сервера

```bash
npm run dev
```

#### 3. Білд для продакшену

```bash
npm run build
npm run preview  # Попередній перегляд білду
```

## Тестування API

### 1. Базові ендпоінти

```bash
# Отримати список коментарів
curl http://localhost:8000/api/comments/

# Створити коментар (потрібна авторизація)
curl -X POST http://localhost:8000/api/comments/ \
  -H "Content-Type: application/json" \
  -d '{"content": "Test comment", "author_name": "Test User"}'
```

### 2. Django Admin

- Відкрийте <http://localhost:8000/admin>
- Увійдіть з credentials: `admin` / `admin123`

## Troubleshooting

### Docker Issues

```bash
# Переглянути статус контейнерів
docker-compose ps

# Перебудувати контейнери
docker-compose up --build

# Очистити весь Docker кеш
docker system prune -a
```

### Database Issues

```bash
# Подключитися до БД в контейнері
docker-compose exec db psql -U postgres -d comments_db

# Скинути БД
docker-compose exec backend python manage.py flush
```

### Port Conflicts

Якщо порти зайняті, змініть їх у `docker-compose.yml`:

```yaml
ports:
  - "8001:8000"  # змініть 8000 на 8001
  - "3001:3000"  # змініть 3000 на 3001
```
