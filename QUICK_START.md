# Comment System - Повна Інструкція по Запуску та Деплою

## Швидкий Старт

### 1. Локальний Запуск (Docker)

```bash
# Клонуйте репозиторій
git clone <your-repo>
cd comment-system

# Зробіть скрипти виконуваними
chmod +x *.sh

# Запустіть додаток
./start.sh
```

**Доступні сервіси:**

- **Frontend**: <http://localhost:3000>
- **Backend API**: <http://localhost:8000>
- **Django Admin**: <http://localhost:8000/admin> (admin/admin123)
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

### 2. Мануальний Запуск (Без Docker)

**Backend:**

```bash
cd backend
pip install -r requirements.txt
cp .env.dev .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

## Production Деплой

### AWS Деплой

```bash
# Налаштування змінних середовища
export AWS_REGION="us-east-1"
export AWS_ACCOUNT_ID="123456789012"
export CLUSTER_NAME="comment-system-cluster"
export SERVICE_NAME="comment-system"

# Запуск деплою
./deploy-aws.sh
```

### Google Cloud Деплой

```bash
# Налаштування змінних середовища
export PROJECT_ID="your-project-id"
export REGION="us-central1"
export SERVICE_NAME="comment-system"

# Запуск деплою
./deploy-gcp.sh
```

### Kubernetes Деплой

```bash
# Застосування manifests
kubectl apply -f k8s/

# Перевірка статусу
kubectl get pods -n comment-system
```

## Тестування

### Основні Тести

```bash
# Всі тести
make test

# Backend тести
make test-backend

# Frontend тести
make test-frontend

# Тести з покриттям
make test-coverage
```

### Навантажувальне Тестування

```bash
# Запуск навантажувальних тестів
./load-test.sh

# Або використання Makefile
make load-test
```

## Корисні Команди

### Управління Додатком

```bash
# Запустити
make dev

# Зупинити
make dev-stop

# Очистити (всі дані)
make dev-clean

# Подивитися логи
make dev-logs
```

### База Даних

```bash
# Міграції
make db-migrate

# Створення міграцій
make db-makemigrations

# Очищення БД
make db-reset

# Бекап БД
make db-backup

# Консоль БД
make db-shell
```

### Моніторинг

```bash
# Статус сервісів
make status

# Перевірка здоров'я
make health

# Логи окремих сервісів
make logs-backend
make logs-frontend
make logs-db
```

## Безпека та Оптимізація

### Перевірка Безпеки

```bash
# Перевірка безпеки
make security-check

# Виправлення проблем безпеки
make security-fix
```

### Якість Коду

```bash
# Лінтинг
make lint

# Форматування
make format
```

## Моніторинг та Логування

### Grafana Дашборд

- **URL**: <http://localhost:3001>
- **Логін**: admin
- **Пароль**: admin (change in .env)

### Prometheus Метрики

- **URL**: <http://localhost:9090>

### Логи Додатку

```bash
# Всі логи
docker-compose logs -f

# Логи конкретного сервісу
docker-compose logs -f backend
docker-compose logs -f frontend
```

## Troubleshooting

### Поширені Проблеми

**1. Порти зайняті:**

```bash
# Подивитися, що використовує порт
sudo lsof -i :3000
sudo lsof -i :8000

# Вбити процес
sudo kill -9 <PID>
```

**2. Docker проблеми:**

```bash
# Очистити Docker кеш
docker system prune -a

# Перестворити контейнери
docker-compose down
docker-compose up --build
```

**3. Проблеми з БД:**

```bash
# Підключитися до БД
docker-compose exec db psql -U postgres -d comments_db

# Перестворити міграції
docker-compose exec backend python manage.py migrate --fake-initial
```

## Архітектура Проекту

### Структура Папок

``
comment-system/
├── backend/                 # Django REST API
│   ├── comments/            # Основний додаток коментарів
│   ├── users/               # Користувачі та аутентифікація
│   ├── files/               # Завантаження файлів
│   ├── analytics/           # Аналітика та метрики
│   └── core/                # Налаштування проекту
├── frontend/                # Vue.js SPA
│   ├── src/
│   │   ├── components/      # Компоненти Vue
│   │   ├── views/           # Сторінки
│   │   ├── store/           # Pinia state management
│   │   └── services/        # API клієнт
├── docker-compose.yml       # Локальна розробка
├── docker-compose.prod.yml  # Продакшен
├── Makefile                 # Команди автоматизації
└── README.md               # Документація
``

### Технологічний Стек

**Backend:**

- **Django 4.2** + **Django REST Framework**
- **PostgreSQL** (основна БД)
- **Redis** (кешування та Celery)
- **Celery** (фонові задачі)
- **JWT Authentication**

**Frontend:**

- **Vue.js 3** + **Composition API**
- **Vite** (білд тул)
- **Pinia** (стейт менеджмент)
- **Vue Router** (маршрутизація)
- **Axios** (HTTP клієнт)

**DevOps:**

- **Docker** + **Docker Compose**
- **Kubernetes** (production)
- **Prometheus** + **Grafana** (моніторинг)
- **CI/CD** (GitHub Actions)

## Подальша Розробка

### Middle Рівень Інтеграцій

1. **GraphQL API** - для гнучких запитів
2. **Elasticsearch** - для швидкого пошуку
3. **RabbitMQ/Kafka** - для асинхронної обробки
4. **Cloud Deployment** - AWS/GCP/Azure

### Middle+ Рівень

1. **Масштабування** для 1M повідомлень/день
2. **Load Balancing** та **Auto Scaling**
3. **Навантажувальне тестування**
4. **Оптимізація продуктивності**

---

**ВДодаток готовий до роботи!** По всіх питаннях дивіться `README.md` та `DEPLOYMENT.md`
