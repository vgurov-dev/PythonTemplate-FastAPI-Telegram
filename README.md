# FastAPI Template

DDD-архитектура для FastAPI-проекта с PostgreSQL, Redis, Celery.

## Описание

Шаблон для создания FastAPI-сервисов с использованием:
- **FastAPI** — веб-фреймворк
- **SQLModel** — ORM (поверх SQLAlchemy)
- **PostgreSQL** — база данных
- **Redis** — кэширование и Celery broker
- **Celery** — фоновые задачи
- **Alembic** — миграции БД
- **JWT** — авторизация
- **Structlog** — логирование
- **Poetry** — управление зависимостями

## Структура

```
my-service/
├── app/                   # Конфигурация, БД, кэш, исключения, точка входа
├── domain/                # Доменный слой (сущности, доменные сервисы)
├── application/            # Слой приложения (DTO, use cases)
├── infrastructure/         # Инфраструктурный слой
│   ├── database/          # SQLAlchemy модели, репозитории
│   ├── cache/            # Redis кэш
│   └── tasks/            # Celery задачи
├── api/                   # API роутеры
├── tests/                 # Тесты (pytest)
├── alembic/               # Миграции
└── pyproject.toml         # Poetry конфиг
```

## Быстрый старт

### Установка

```bash
poetry install
```

### Настройка

```bash
cp .env.example .env
# Отредактируй .env
```

### Запуск

```bash
poetry run uvicorn app.main:app --reload
```

## Docker

```bash
docker-compose up --build
```

## Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `APP_NAME` | Название приложения | my-service |
| `DATABASE_URL` | URL PostgreSQL | postgresql+asyncpg://user:password@localhost:5432/myservice |
| `REDIS_URL` | URL Redis | redis://localhost:6379/0 |
| `JWT_SECRET_KEY` | Секретный ключ JWT | your-secret-key-here |
| `LOG_LEVEL` | Уровень логирования | INFO |

## API Endpoints

- `GET /` — Главная
- `GET /health` — Health check

## Разработка

```bash
# Тесты
poetry run pytest

# Миграции
poetry run alembic migrate -m "message"
poetry run alembic upgrade head
```