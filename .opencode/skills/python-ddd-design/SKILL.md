---
name: python-ddd-design
description: DDD architecture and asyncio best practices for Python
license: MIT
compatibility: opencode
metadata:
  audience: backend-developers
  workflow: backend
---

# Python DDD Design

## Роль

Python бэкенд разработчик с DDD и asyncio.

## Принципы

### DDD Архитектура

- **Раскладывать код на слои**: `domain/`, `application/`, `infrastructure/`, `api/`
  - ✅ Хорошо: `domain/services/token.py`, `application/actions/auth/login.py`
  - ❌ Плохо: Вся логика в одном файле `models.py` или `views.py`

- **Файл должен быть поделен на DDD модули**
  - ✅ Хорошо: entities, services, repositories в разных файлах
  - ❌ Плохо: Всё в одном файле `user.py` (500+ строк)

- **Проверять структуру папок на конфликты имен**
  - ✅ Хорошо: `bootstrap/` + `application/` (разные смыслы)
  - ❌ Плохо: `app/` + `application/` (почти одно и то же)

### DDD Слои

| Слой | Назначение | Что внутри |
|------|-----------|-----------|
| **domain** | Бизнес-логика | entities, services, value objects |
| **application** | Use cases | actions (login, register), dto |
| **infrastructure** | Инфраструктура | database, cache, tasks |
| **api** | Оркестрация | routers, depends |
| **bootstrap** | Инициализация | config, database, main |

#### Хорошо vs Плохо для слоев

- **Domain слой**
  - ✅ Хорошо: `TokenDomainService.create_token()` проверяет срок жизни
  - ❌ Плохо: `jwt.encode()` напрямую в API роутере

- **Application слой**
  - ✅ Хорошо: `LoginAction.execute()` — один метод делает логин
  - ❌ Плохо: Писать логику прямо в `api/routers/`

- **Infrastructure слой**
  - ✅ Хорошо: Репозитории в `infrastructure/database/repositories/`
  - ❌ Плохо: Смешивать DB логику с domain entities

- **API слой**
  - ✅ Хорошо: Роутер импортирует `LoginAction`, вызывает, возвращает response
  - ❌ Плохо: Логика валидации, бизнес-правила в роутере

### Asyncio Best Practices

- **Писать асинхронный код**
  - ✅ Хорошо: `async def get_user(telegram_id: int) -> User:`
  - ❌ Плохо: Синхронные функции в async контексте

- **Использовать async with для ресурсов**
  - ✅ Хорошо:
    ```python
    async with AsyncSession(engine) as session:
        result = await session.execute(query)
    ```
  - ❌ Плохо: Сессия открыта без контекстного менеджера

- **Не блокироватьevent loop**
  - ✅ Хорошо: `await asyncio.gather(*tasks)` для параллельных задач
  - ❌ Плохо: Синхронный цикл `for item in items: await process(item)`

- **Использовать proper await**
  - ✅ Хорошо:
    ```python
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    ```
  - ❌ Плохо: `time.sleep(1)` в async функции (блокирует!)

- **Type hints для async**
  - ✅ Хорошо: `async def get_user(telegram_id: int) -> User | None:`
  - ❌ Плохо: `async def get_user(telegram_id):` (без типов)

### Размер файлов и методов

- **Не писать много кода в одном файле**
  - ✅ Хорошо: Файл 50-100 строк, один класс/сервис
  - ❌ Плохо: Файл 500+ строк со всем подряд

- **Избегать длинных методов**
  - ✅ Хорошо: Метод ≤ 20-30 строк, делает одно дело
  - ❌ Плохо: Метод на 100 строк с 5 уровнями вложенности

- **Разбивать по логическим действиям**
  - ✅ Хорошо: `UserRegistrationAction` → `validate_input` → `check_existing` → `create_user`
  - ❌ Плохо: Один метод `register_user()` на 200 строк

### Именование (DDD)

- **Использовать DDD для именования классов**
  - ✅ Хорошо: `TokenDomainService`, `LoginAction`, `UserEntity`
  - ❌ Плохо: `TokenHelper`, `LoginController`, `UserData`

- **Именовать файлы по смыслу**
  - ✅ Хорошо: `domain/services/token.py`, `application/dto/auth.py`
  - ❌ Плохо: `utils.py`, `helpers.py`, `misc.py`

### DRY и KISS

- **Следовать DRY (Don't Repeat Yourself)**
  - ✅ Хорошо: Вынести повторяющуюся валидацию в `validation_utils.py`
  - ❌ Плохо: Копировать валидацию в 5 мест

- **Следовать KISS (Keep It Simple, Stupid)**
  - ✅ Хорошо: Простая функция `is_valid_email(email: str) -> bool`
  - ❌ Плохо: Сложные вложенные условия

### Тесты (отдельная тема — tdd-test-development-python)

- **Разделять unit и integration тесты**
  - ✅ Хорошо: unit тесты — мокаем всё; integration — реальные DB
  - ❌ Плохо: Смешивать unit и integration в одном файле

- **Запускать отдельно**
  - ✅ Хорошо: `pytest -m unit` и `pytest -m integration` раздельно
  - ❌ Плохо: Запускать всё вместе без маркировки

## Workflow

1. **Анализ**: Понять требования, предложить структуру классов по DDD
2. **Проектирование**: Нарисовать диаграмму слоев
3. **Согласование**: Обсудить структуру с пользователем
4. **Реализация**: Писать код по слоям DDD
5. **Проверка**: Запустить линтеры и тесты
6. **Анализ warnings**: Проверить warnings перед коммитом

## Примеры из опыта

### Хорошо

- **DDD структура**: `domain/services/token.py` — TokenDomainService создает и верифицирует токены
- **Actions**: `application/actions/auth/login.py` — LoginAction делает одно дело (логин)
- **DTO**: `application/dto/auth.py` — LoginRequest, TokenResponse
- **DI в роутерах**: Через Depends + lru_cache

### Плохо (исправлено)

- **Конфликт имен**: `app/` + `application/` → исправлено в `bootstrap/`
- **Много volumes**: 9 отдельных → 1 volume `./src/backend/:/app/`
- **Лишние проверки**: После `create_token` сразу `verify_token` → убрано
- **Неправильные исключения**: `InvalidTokenError` конфликтовал с jwt → переименовано в `TokenInvalidError`

## Ссылки

- Другие скиллы: `python-backend-developer`, `tdd-test-development-python`
- Docker: `docker-compose-dev`
- Bot: `bot-handlers`