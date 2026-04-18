# Telegram Template

Монолит-шаблон для Telegram-проектов: Bot + WebApp + Backend.

## Архитектура

```
src/
├── backend/     # FastAPI + PostgreSQL + Redis + Celery
├── bot/         # aiogram 3 Telegram бот
├── webapp/      # React Telegram Web App
└── kit/         # Общие утилиты
```

## Модули

| Модуль | Описание | Порт | Stack |
|--------|----------|------|-------|
| Backend | REST API | 8000 | FastAPI, SQLModel, PostgreSQL |
| Bot | Telegram bot | — | aiogram 3, Redis |
| WebApp | Frontend | 3000 | React, Vite |

## Быстрый старт

### Требования

- Python 3.12+
- Node.js 20+
- Docker + Docker Compose

### Установка

```bash
# Клонирование
git clone https://github.com/vgurov-dev/telegram-template.git
cd telegram-template

# Зависимости
poetry install --with backend,bot

# Настройка
cp .env.example .env
```

### Запуск

```bash
# Локально (backend + bot)
poetry run uvicorn src.backend.app.main:app --reload --port 8000

# Docker Compose (все сервисы)
docker-compose up --build
```

###.env

| Переменная | Описание | По умолчанию |
|------------|----------|-------------|
| `APP_NAME` | Название приложения | my-service |
| `DATABASE_URL` | URL PostgreSQL | postgresql+asyncpg://user:password@postgres:5432/myservice |
| `REDIS_URL` | URL Redis | redis://localhost:6379/0 |
| `BOT_TOKEN` | Telegram bot token | — |
| `JWT_SECRET_KEY` | Секретный ключ JWT | your-secret-key-here |

## Разработка

### Backend

```bash
# Запуск
poetry run uvicorn src.backend.app.main:app --reload

# Тесты
poetry run pytest src/backend/tests/

# Миграции
poetry run alembic migrate -m "message"
poetry run alembic upgrade head
```

### Bot

```bash
# Запуск
poetry run python -m src.bot.main
```

### WebApp

```bash
cd src/webapp
npm install
npm run dev
```

## Docker Compose

| Файл | Назначение |
|------|-------------|
| `docker-compose.yml` | Локальная разработка |
| `docker-compose.staging.yml` | Staging / production |

## CI/CD

- **CI** — GitHub Actions: lint, test, build
- **CD** — Пуш образов в GHCR на `main`

## Структура проекта

```
telegram-template/
├── src/
│   ├── backend/          # FastAPI
│   │   ├── app/         # Конфигурация
│   │   ├── domain/      # Сущности
│   │   ├── application/ # Use cases
│   │   ├── infrastructure/ # DB, cache
│   │   ├── api/        # Роутеры
│   │   └── tests/      # Тесты
│   ├── bot/             # Telegram бот
│   │   ├── handlers/   # Обработчики
│   │   └── services/   # Сервисы
│   ├── webapp/          # React
│   │   └── src/        # Компоненты
│   └── kit/             # Shared
├── .github/workflows/   # CI/CD
├── docker-compose.yml   # Локальный запуск
└── pyproject.toml      # Poetry
```

## License

MIT