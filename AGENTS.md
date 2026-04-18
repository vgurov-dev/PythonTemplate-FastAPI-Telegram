# Правила генерации кода

## Общие правила

### Docker
- При монтировании `./src/bot:/app` → command: `python -m bot.main`
- При монтировании `./src/backend:/app` → command: `uvicorn app.main:app`
- Все сервисы в docker-compose.staging.yml должны использовать образы из GHCR
- Для мониторинга использовать официальные образы (nginx, prometheus, grafana и т.д.)

### Python модули
- Все Python пакеты устанавливаются через Poetry, НЕ pip
- Использовать группы: `backend`, `bot`, `dev`
- Пример: `poetry install --with backend,bot`

### Imports
- Клавиатуры бота: `from bot.keyboards.registration import ...`
- НЕ: `from bot.handlers.keyboards import ...`

## Backend слой

### Структура (DDD)
```
src/backend/
├── app/              # Точка входа, конфигурация
├── domain/           # Сущности (entities) + services (domain logic)
├── application/     # actions (use cases), DTO
├── infrastructure/   # DB, cache, tasks
└── api/            # Роутеры FastAPI (только orchestration)
```

### DDD Правила
- Все business logic в domain/services/
- Use cases в application/actions/{group}/
- Pydantic схемы в application/dto/
- API routers только orchestration (вызов actions, возврат response)
- НЕ: логика в api/routers/ — только импорт и вызов
- НЕ: валидация в domain — только application/dto/

### Примеры (DDD)
- ПРАВИЛЬНО: `from domain.services.token import TokenDomainService`
- ПРАВИЛЬНО: `from app.actions.auth.login import LoginAction`
- ПРАВИЛЬНО: `from application.dto.auth import LoginRequest`
- НЕПРАВИЛЬНО: `jwt.encode()` в api/routers/
- НЕПРАВИЛЬНО: бизнес-логика в domain entities

### API
- Все endpoint защищать сDepends(verify_service_token) для межсервисной auth
- Использовать JWT для пользовательской авторизации
- response_model через Pydantic схемы

### База данных
- SQLModel для моделей
- AsyncSession для работы с БД
- Репозитории в `infrastructure/database/repositories/`

## Bot слой

### Структура
```
src/bot/
├── app/            # Конфигурация
├── handlers/       # Обработчики сообщений (НЕ клавиатуры!)
├── keyboards/     # Клавиатуры (InlineKeyboardButton)
├── services/      # Бизнес-логика
├── models/       # Модели SQLAlchemy
└── tasks/       # Celery tasks
```

### Регистрация пользователей
- Таблица signups: telegram_id, username, first_name, status (NOT_CONFIRMED/CONFIRMED)
- После подтверждения → синхронизация с backend через Celery task
- Использовать service_token для auth

## WebApp слой

### Структура
```
src/webapp/
├── src/
│   ├── components/
│   ├── pages/
│   ├── hooks/
│   └── services/
├── package.json
└── vite.config.ts
```

### Стек
- React 18 + Vite
- TypeScript
- @twa-dev/twa-sdk для Telegram Web App

## Соглашения об именовании

### Файлы
- Python: `snake_case.py`
- TypeScript: `camelCase.ts`
- Конфиги: `snake_case.*`

### Переменные окружения
- Все в `.env.example`
- Описания в комментариях
- Использовать `validation_alias` в Pydantic

### Git
- Коммиты по слоям: `feat(bot):`, `feat(backend):`, `refactor:`, `fix:`
- Ветки: `feature/`, `fix/`, `hotfix/`

## CI/CD

### GitHub Actions
- CI: lint + test + build на push
- CD: пуш в GHCR на merge в main
- Docker образы тегировать по git tag

## Skills

### /.opencode/skills/docker-compose/SKILL.md
- Все сервисы запускать через docker-compose
- Не использовать poetry run напрямую
- Smoke test: docker-compose up -d + curl
- Тесты: docker-compose exec {service} pytest

### /.opencode/skills/bot/SKILL.md
- Inline keyboard: удалять сообщение после нажатия кнопки
- Обязательно вызывать callback.answer()
- Создавать новое сообщение вместо старого