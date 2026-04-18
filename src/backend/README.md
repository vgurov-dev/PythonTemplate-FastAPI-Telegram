# Backend

FastAPI сервис с PostgreSQL, Redis, Celery.

## Стек

- **FastAPI** — веб-фреймворк
- **SQLModel** — ORM
- **PostgreSQL** — база данных
- **Redis** — кэширование / Celery broker
- **Celery** — фоновые задачи
- **Alembic** — миграции
- **JWT** — авторизация

## Структура

```
backend/
├── app/              # Точка входа, конфигурация
├── domain/            # Сущности, доменные сервисы
├── application/       # Use cases, DTO
├── infrastructure/    # Database, cache, tasks
├── api/              # Роутеры
├── tests/            # Тесты
└── alembic/          # Миграции
```

## Переменные окружения

| Переменная | Описание |
|------------|----------|
| `APP_NAME` | Название |
| `DATABASE_URL` | URL PostgreSQL |
| `REDIS_URL` | URL Redis |
| `JWT_SECRET_KEY` | Секрет JWT |
| `CELERY_BROKER_URL` | Celery broker |

## Запуск

```bash
poetry install --with backend
poetry run uvicorn app.main:app --reload
```

## Тесты

```bash
poetry run pytest src/backend/tests/ -v
```

## API

- `GET /` — главная
- `GET /health` — health check