# Локальне Тестування - Готовий до Запуску

## Що Створено

### Скрипти для Автоматизації

- filepath>check-prerequisites.sh</filepath> - Перевірка системних вимог
- filepath>start.sh</filepath> - Швидкий запуск додатку
- filepath>health-check.sh</filepath> - Перевірка здоров'я сервісів
- filepath>test-functionality.sh</filepath> - Функціональне тестування
- filepath>stop.sh</filepath> - Зупинка додатку
- filepath>clean.sh</filepath> - Очищення даних
- filepath>load-test.sh</filepath> - Навантажувальне тестування

### Документація

- filepath>LOCAL_TESTING_GUIDE.md</filepath> - Детальна інструкція
- filepath>README.md</filepath> - Основна документація
- filepath>QUICK_START.md</filepath> - Швидкий старт

### Конфігурація

- filepath>docker-compose.yml</filepath> - Docker для розробки
- filepath>Makefile</filepath> - Команди автоматизації
- Environment файли (.env)

## Покрокова Інструкція для Тестування

### Перевірка Передумов

```bash
# Зробити скрипти виконуваними (якщо потрібно)
chmod +x *.sh

# Перевірити системні вимоги
./check-prerequisites.sh
```

**Очікуваний результат:**

``

Comment System Prerequisites Check

======================================
docker is installed
docker-compose is installed  
git is installed
curl is installed
Port 3000 is available
Port 8000 is available
All prerequisites are met!
``

### Запуск Додатку

```bash
# Швидкий запуск
./start.sh
```

**Очікуваний результат:**

``
Starting Comment System Application...
Stopping existing containers...
Building and starting containers...
Waiting for services to be ready...
Checking service status...
Creating Django superuser...
Application started successfully!

Frontend: <http://localhost:3000>
Backend API: <http://localhost:8000>
Django Admin: <http://localhost:8000/admin>

``

### Перевірка Здоров'я

```bash
# Перевірити всі сервіси
./health-check.sh
```

**Очікуваний результат:**

``

Comment System Health Check

==================================

Docker is running
backend is running
frontend is running  
db is running
redis is running
Backend API is responding
Frontend is responding
All systems are healthy!
``

### Функціональне Тестування

```bash
# Протестувати API і функціональність
./test-functionality.sh
```

**Очікуваний результат:**

``

Comment System Functional Tests

===================================

PASSED: Backend Health Check
PASSED: API Root Endpoint
PASSED: Comments List API
PASSED: Create Comment via API
PASSED: Frontend Accessibility
PASSED: Django Admin Accessibility
All tests passed! Ready for production!
``

### Навантажувальне Тестування (Опціонально)

```bash
# Перевірити продуктивність
./load-test.sh
```

## Доступ до Сервісів

### Frontend (Vue.js)

- **URL**: <http://localhost:3000>
- **Опис**: Основний користувацький інтерфейс
- **Тест**: Відкрити в браузері, додати коментар

### Backend API (Django)

- **URL**: <http://localhost:8000/api/>
- **Опис**: REST API endpoints
- **Тест**:

  ```bash
  curl http://localhost:8000/api/comments/
  ```

### Django Admin

- **URL**: <http://localhost:8000/admin>
- **Логін**: admin
- **Пароль**: admin123
- **Тест**: Логін через браузер

### База Даних (PostgreSQL)

- **Host**: localhost:5432
- **DB**: comments_db
- **User**: postgres
- **Password**: postgres123

### Cache (Redis)

- **Host**: localhost:6379
- **Тест**:

  ```bash
  docker-compose exec redis redis-cli ping
  ```

## Тестові Сценарії

### API Тестування

```bash
# 1. Отримати список коментарів
curl -X GET http://localhost:8000/api/comments/

# 2. Створити новий коментар
curl -X POST http://localhost:8000/api/comments/ \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Мій тестовий коментар",
    "author_name": "Test User",
    "author_email": "test@example.com"
  }'

# 3. Перевірити що коментар створено
curl -X GET http://localhost:8000/api/comments/
```

### Frontend Тестування

1. Відкрити <http://localhost:3000> в браузері
2. Перевірити чи завантажується сторінка
3. Знайти форму для додавання коментарів
4. Додати тестовий коментар
5. Перевірити що коментар з'явився в списку

## ⚡ Швидкі Команди

### Через Makefile

```bash
make check-prerequisites  # Перевірка передумов
make dev                 # Запуск додатку
make health-check        # Перевірка здоров'я  
make test-functionality  # Функціональні тести
make quick-test         # Здоров'я + функціональні тести
make dev-stop           # Зупинка
```

### Безпосередньо

```bash
./check-prerequisites.sh  # Перевірка передумов
./start.sh               # Запуск
./health-check.sh        # Здоров'я сервісів
./test-functionality.sh  # Функціональні тести  
./stop.sh               # Зупинка
./clean.sh              # Очищення даних
```

## Troubleshooting

### Якщо щось не працює

1. **Перевірити статус контейнерів:**

   ```bash
   docker-compose ps
   ```

2. **Подивитися логи:**

   ```bash
   docker-compose logs -f
   ```

3. **Перезапустити:**

   ```bash
   ./stop.sh
   ./start.sh
   ```

4. **Очистити і перезапустити:**

   ```bash
   ./clean.sh
   ./start.sh
   ```

5. **Перевірити порти:**

   ```bash
   sudo lsof -i :3000
   sudo lsof -i :8000
   ```

## Чек-лист Готовності

Після успішного проходження всіх кроків:

- [ ] Prerequisites check пройшов
- [ ] Додаток запускається без помилок
- [ ] Health check показує всі сервіси як "healthy"
- [ ] Functional tests проходять успішно
- [ ] Frontend доступний в браузері
- [ ] API відповідає на запити
- [ ] Django Admin працює
- [ ] Можна створювати коментарі
- [ ] Коментарі зберігаються в БД

## Результат

**Якщо всі тести пройшли успішно, ваша система готова!**

### Наступні кроки

1. **Локальне тестування завершено**
2. **Готово до Production Deployment**
3. **Можна переходити до масштабування**

---

**Готово до Production Deployment!**
Перехід до наступного етапу: **Production Deployment та Cloud Setup**
