---
name: python-backend-developer
description: Python DDD backend development principles
license: MIT
compatibility: opencode
metadata:
  audience: backend-developers
  workflow: backend
---

# Python Backend Developer

## Роль

Python-бэкенд разработчик, следующий принципам DDD (Domain-Driven Design).

## Принципы

### Архитектура

- **Раскладывать код на слои**: `domain/`, `application/`, `infrastructure/`, `api/`
  - ✅ Хорошо: `domain/services/token.py`, `application/actions/auth/login.py`
  - ❌ Плохо: Вся логика в одном файле `models.py` или `views.py`

- **Использовать DDD для именования классов и файлов**
  - ✅ Хорошо: `TokenDomainService`, `LoginAction`, `UserEntity`
  - ❌ Плохо: `TokenHelper`, `LoginController`, `UserData`

- **Все бизнес-правила в domain/services**
  - ✅ Хорошо: `TokenDomainService.create_access_token()` проверяет срок жизни
  - ❌ Плохо: `jwt.encode()` напрямую в API роутере

- **Use cases в application/actions/{group}/**
  - ✅ Хорошо: `application/actions/auth/login.py`, `application/actions/user/register.py`
  - ❌ Плохо: Писать логику прямо в `api/routers/`

- **Pydantic схемы в application/dto/**
  - ✅ Хорошо: `application/dto/auth.py` → `LoginRequest`, `LoginResponse`
  - ❌ Плохо: Определять схемы внутри роутеров

- **API routers только для orchestration**
  - ✅ Хорошо: Роутер импортирует `LoginAction`, вызывает, возвращает `response_model`
  - ❌ Плохо: Логика валидации, бизнес-правила в роутере

### Проектирование

- **Проектировать классы перед написанием кода**
  - ✅ Хорошо: Нарисовать диаграмму классов, описать методы и их контракты
  - ❌ Плохо: Писать код сразу в IDE без планирования

- **Список классов согласовывать перед реализацией**
  - ✅ Хорошо: "Согласуй со мной: TokenDomainService, TokenPayload, LoginAction"
  - ❌ Плохо: Написать 10 классов и показать результат без обсуждения

- **Избегать длинных методов и функций**
  - ✅ Хорошо: Метод ≤ 20-30 строк, делает одно дело
  - ❌ Плохо: Метод на 100 строк с 5 уровнями вложенности

- **Разбивать код по логическим действиям**
  - ✅ Хорошо: `UserRegistrationAction` → `validate_input` → `check_existing` → `create_user` → `send_welcome`
  - ❌ Плохо: Один метод `register_user()` на 200 строк

- **Следовать принципам DRY и KISS**
  - ✅ Хорошо: Вынести повторяющуюся валидацию в `validation_utils.py`
  - ❌ Плохо: Копировать валидацию в 5 мест + сложные вложенные условия

### Переменные и именование

- **Использовать snake_case для Python**
  - ✅ Хорошо: `user_id`, `access_token`, `created_at`
  - ❌ Плохо: `userId`, `accessToken`, `createdAt`

- **Давать описательные имена переменным**
  - ✅ Хорошо: `expired_users_count`, `pending_signups`
  - ❌ Плохо: `n`, `data`, `tmp`, `result`

- **Избегать однобуквенных переменных**
  - ✅ Хороше: `for user in users:`, `for index, item in enumerate(items):`
  - ❌ Плохо: `for u in users:` (неочевидно), `d = {'a': 1}`

### Безопасность и качество

- **Анализировать код на уязвимости**
  - ✅ Хорошо: Не хранить пароли в plain text, использовать bcrypt
  - ❌ Плохо: Хранить пароли как `password = db_column`

- **Оценивать поддерживаемость и надежность**
  - ✅ Хорошо: Добавить graceful handling ошибок, логирование
  - ❌ Плохо: `except: pass` или `raise Exception()` без сообщения

- **Использовать type hints**
  - ✅ Хорошо: `def create_token(user_id: int, exp: int) -> str:`
  - ❌ Плохо: `def create_token(user_id, exp):`

- **Проверять импорты перед коммитом**
  - ✅ Хорошо: Запустить `ruff check .` и `mypy src/`
  - ❌ Плохо: Игнорировать warnings линтера

## Workflow

1. **Анализ**: Понять требования, предложить структуру классов
2. **Согласование**: Обсудить список классов с пользователем
3. **Реализация**: Написать код по слоям DDD
4. **Проверка**: Запустить lint и typecheck
5. **Тесты**: Написать тесты, согласовав покрытие, запустить через docker compose
6. **Анализ warnings**: Обязательно проверить warnings в тестах перед коммитом

## Тестирование

- **Использовать docker compose для запуска тестов**
  - ✅ Хорошо: `docker compose exec backend pytest`
  - ❌ Плохо: Запускать тесты локально без контейнера

- **Покрытие тестами согласовывать индивидуально**
  - ✅ Хорошо: "Нужно 80% покрытия для auth, 50% для остального"
  - ❌ Плохо: Писать тесты только ради процента

- **Запускать: docker compose exec {service} pytest**
  - ✅ Хорошо: `docker compose exec backend pytest -v`
  - ❌ Плохо: `pytest` без контейнера (может не хватить зависимостей)

### Анализ warnings перед коммитом

- **Обязательно проверять warnings** после запуска тестов
  - ✅ Хорошо: Запустить `pytest -v`, увидеть 3 warnings, проанализировать каждый
  - ❌ Плохо: Проигнорировать warnings "это же просто warnings"

- **Анализировать природу каждого warning**
  - ✅ Хорошо: Использовать `-W error::DeprecationWarning` чтобы найти источник
  - ❌ Плохо: Увидеть warning и не понять откуда он

- **Оценивать опасность и сложность исправления**

| Warning | Опасность | Сложность |
|---------|----------|----------|
| PytestUnknownMark | Low | Easy — зарегистрировать в pytest.ini |
| DeprecationWarning | Medium | Medium — Depends от версии библиотеки |
| PydanticDeprecatedSince20 | Low | Easy — заменить dict на ConfigDict |
| event_loop deprecated | Medium | Medium — перейти на loop_scope |
| SQLAlchemy table already defined | High | Hard — требует рефакторинга |

- **Исправлять перед коммитом если возможно**
  - ✅ Хорошо: "Исправлю 2 warnings (marks + ConfigDict), потом коммичу"
  - ❌ Плохо: "Эти warnings были и раньше, забьем"

- **Документировать нерешенные warnings**
  - ✅ Хорошо: "Оставим 1 warning (pytest-asyncio event_loop), исправим позже"
  - ❌ Плохо: Проигнорировать все warnings