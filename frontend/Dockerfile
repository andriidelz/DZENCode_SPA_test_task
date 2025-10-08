FROM node:18-alpine

# Встановлення робочої директорії
WORKDIR /app

# Копіювання package.json та package-lock.json
COPY package*.json ./

# Встановлення залежностей
RUN npm ci

# Копіювання коду
COPY . .

# Експорт порту
EXPOSE 3000

# Команда за замовчуванням
CMD ["npm", "run", "dev"]
