FROM python:3.11-slim

# Встановлення системних залежностей
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Встановлення робочої директорії
WORKDIR /app

# Копіювання requirements і встановлення Python залежностей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копіювання коду
COPY . .

# Створення директорій для медіа та статичних файлів
RUN mkdir -p media static

# Експорт порту
EXPOSE 8000

# Команда за замовчуванням
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
