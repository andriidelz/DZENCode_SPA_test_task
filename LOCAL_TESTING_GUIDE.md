# Локальне Тестування - Покрокова Інструкція

## Передумови

### Необхідне ПЗ

- **Docker** (версія 20.10+)
- **Docker Compose** (версія 2.0+)
- **Git**

### Перевірка встановлення

```bash
# Перевірити Docker
docker --version
docker-compose --version

# Перевірити чи Docker запущений
docker info
```

## Крок 1: Підготовка Проекту

### 1.1 Клонування (якщо потрібно)

```bash
git clone <your-repo-url>
cd comment-system
```

### 1.2 Зробити скрипти виконуваними

```bash
chmod +x *.sh
```

### 1.3 Перевірити структуру файлів

```bash
ls -la
# Повинні бути: start.sh, stop.sh, clean.sh, docker-compose.yml
```

## Крок 2: Запуск Додатку

### 2.1 Швидкий запуск

```bash
./start.sh
```

**Що відбувається:**

- Зупинка існуючих контейнерів
- Побудова Docker images
- Запуск всіх сервісів
- Створення БД та міграції
- Створення superuser (admin/admin123)

### 2.2 Очікувані повідомлення

``
Starting Comment System Application...
Stopping existing containers...
Building and starting containers...
Waiting for services to be ready...
Checking service status...
Creating Django superuser...
Application started successfully!
``

### 2.3 Альтернативний запуск (ручний)

```bash
# Якщо start.sh не працює
docker-compose down
docker-compose up --build -d
docker-compose ps
```

## Крок 3: Перевірка Сервісів

### 3.1 Доступні URL

- **Frontend**: <http://localhost:3000>
- **Backend API**: <http://localhost:8000>
- **Django Admin**: <http://localhost:8000/admin>
- **API Root**: <http://localhost:8000/api/>

### 3.2 Тест Frontend

```bash
# Перевірити доступність
curl -f http://localhost:3000/

# Очікуваний результат: HTML сторінка Vue.js
```

### 3.3 Тест Backend API

```bash
# Health check
curl -f http://localhost:8000/health/

# API endpoints
curl http://localhost:8000/api/
curl http://localhost:8000/api/comments/

# Очікуваний результат: JSON response
```

### 3.4 Django Admin

1. Відкрити: <http://localhost:8000/admin>
2. Логін: `admin`
3. Пароль: `admin123`

## Крок 4: Тестування Функціональності

### 4.1 API Тести

#### Отримати коментарі

```bash
curl -X GET http://localhost:8000/api/comments/ \
  -H "Content-Type: application/json"
```

#### Створити коментар

```bash
curl -X POST http://localhost:8000/api/comments/ \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Тестовий коментар",
    "author_name": "Test User",
    "author_email": "test@example.com"
  }'
```

#### Перевірити що коментар створено

```bash
curl -X GET http://localhost:8000/api/comments/
```

### 4.2 Frontend Тести

1. **Відкрити браузер**: <http://localhost:3000>
2. **Перевірити UI**:
   - Чи завантажується сторінка
   - Чи є форма для додавання коментарів
   - Чи відображаються існуючі коментарі
3. **Додати коментар через UI**
4. **Перевірити що коментар з'явився**

## Крок 5: Діагностика

### 5.1 Перевірка статусу контейнерів

```bash
docker-compose ps
```

**Очікуваний результат:**

``

Name                   Command               State           Ports

------------------------------------------------------------------

comment-system_backend_1   sh -c python manage.py ...       Up      0.0.0.0:8000->8000/tcp
comment-system_db_1        docker-entrypoint.sh postgres    Up      0.0.0.0:5432->5432/tcp
comment-system_frontend_1  docker-entrypoint.sh npm ...     Up      0.0.0.0:3000->3000/tcp
comment-system_redis_1     docker-entrypoint.sh redis ...   Up      0.0.0.0:6379->6379/tcp
``

### 5.2 Перегляд логів

```bash
# Всі сервіси
docker-compose logs -f

# Конкретний сервіс
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f db
```

### 5.3 Підключення до контейнерів

```bash
# Backend shell
docker-compose exec backend python manage.py shell

# Database shell
docker-compose exec db psql -U postgres -d comments_db

# Frontend shell
docker-compose exec frontend sh
```

## Крок 6: Навантажувальне Тестування

### 6.1 Запуск load tests

```bash
./load-test.sh
```

### 6.2 Альтернативне тестування

```bash
# Простий тест з curl
for i in {1..10}; do
  curl -X POST http://localhost:8000/api/comments/ \
    -H "Content-Type: application/json" \
    -d "{\"content\": \"Load test comment $i\", \"author_name\": \"LoadTester$i\"}"
  echo "Created comment $i"
done
```

## Крок 7: Зупинка та Очищення

### 7.1 Зупинити додаток

```bash
./stop.sh
```

### 7.2 Очистити всі дані

```bash
./clean.sh
# УВАГА: Це видалить ВСІ дані!
```

### 7.3 Часткове очищення

```bash
# Тільки зупинити
docker-compose down

# Зупинити і видалити volumes
docker-compose down -v
```

## Troubleshooting

### Проблема: Порти зайняті

```bash
# Знайти процес на порту
sudo lsof -i :3000
sudo lsof -i :8000

# Вбити процес
sudo kill -9 <PID>
```

### Проблема: Docker не працює

```bash
# Перезапустити Docker
sudo systemctl restart docker

# Перевірити статус
sudo systemctl status docker
```

### Проблема: Помилки міграції БД

```bash
# Скинути БД і мігрувати заново
docker-compose exec backend python manage.py flush --noinput
docker-compose exec backend python manage.py migrate
```

### Проблема: Frontend не збирається

```bash
# Очистити node_modules і перебудувати
docker-compose down
docker-compose build --no-cache frontend
docker-compose up frontend
```

## Критерії Успішного Тестування

### Backend

- Сервер запускається на порту 8000
- Міграції виконуються успішно
- API endpoints відповідають
- Django Admin доступний
- Можна створювати та отримувати коментарі

### Frontend

- Додаток запускається на порту 3000
- Сторінка завантажується в браузері
- API викликає функціонують
- UI інтерфейс працює

### Database

- PostgreSQL працює на порту 5432
- Дані зберігаються і отримуються
- Міграції застосовуються правильно

### Cache

- Redis працює на порту 6379
- Кешування функціонує

## Чек-лист Тестування

### Основна Функціональність

- [ ] Додаток запускається командою `./start.sh`
- [ ] Всі сервіси показують статус "Up"
- [ ] Frontend доступний за <http://localhost:3000>
- [ ] Backend API доступний за <http://localhost:8000>
- [ ] Django Admin працює з credentials admin/admin123
- [ ] Можна створити коментар через API
- [ ] Можна отримати список коментарів
- [ ] Коментарі зберігаються в БД
- [ ] Frontend може відображати коментарі
- [ ] Можна додати коментар через UI

### Performance

- [ ] API відповідає швидко (< 1 секунди)
- [ ] Frontend завантажується швидко
- [ ] Навантажувальні тести проходять успішно

### Зупинка

- [ ] Додаток зупиняється командою `./stop.sh`
- [ ] Всі контейнери зупиняються правильно
- [ ] Дані зберігаються між перезапусками

--

**Після успішного локального тестування можна переходити до production deployment!**
