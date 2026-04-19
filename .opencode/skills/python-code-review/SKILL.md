---
name: python-code-review
description: Code review checklist and best practices for Python
license: MIT
compatibility: opencode
metadata:
  audience: code-reviewers
  workflow: review
---

# Python Code Review

## Роль

Python разработчик, выполняющий code review с чеклистом.

## Принципы

### Pre-Review Чеклист

**Перед просмотром кода — запустить:**

| Инструмент | Команда | Что проверяет |
|------------|---------|---------------|
| ruff | `ruff check .` | Линтинг, imports, стиль |
| black | `black --check .` | Форматирование |
| mypy | `mypy src/backend` | Типы |
| pytest | `pytest -v` | Тесты + warnings |
| poetry | `poetry check` | Зависимости |

- ✅ Хорошо: Все инструменты прошли без ошибок
- ❌ Плохо: Есть ошибки — вернуть автору до review

### Этап 1: Архитектура и структура

- **DDD слои**: Код в правильном слое?
  - ✅ Хорошо: `domain/services/token.py` — TokenDomainService
  - ❌ Плохо: Логика в `api/routers/` или `utils.py`

- **Размер файла**: Не более 100-150 строк?
  - ✅ Хорошо: Файл 50-80 строк с одним классом
  - ❌ Плохо: Файл 300+ строк со всем подряд

- **Импорты**: Нет циклических?
  - ✅ Хорошо: `from domain.services.token import ...`
  - ❌ Плохо: Циклический импорт между слоями

- **Именование файлов**: snake_case, описательные?
  - ✅ Хорошо: `token_service.py`, `login_action.py`
  - ❌ Плохо: `utils.py`, `helpers.py`, `misc.py`

### Этап 2: Качество кода

- **Type hints**: Все функции типизированы?
  - ✅ Хорошо:
    ```python
    def create_token(service_name: str, expires_seconds: int = 86400) -> str:
    ```
  - ❌ Плохо:
    ```python
    def create_token(service_name, expires_seconds=86400):
    ```

- **Async правильно используется?**
  - ✅ Хорошо:
    ```python
    async def get_user(telegram_id: int) -> User | None:
        async with AsyncSession(engine) as session:
            ...
    ```
  - ❌ Плохо: `time.sleep()` в async функции (блокирует!)

- **Обработка ошибок**: Есть try/except где нужно?
  - ✅ Хорошо: Логирование + осмысленные исключения
  - ❌ Плохо: `except: pass` или `raise Exception()`

- **DRY**: Нет дублирования кода?
  - ✅ Хорошо: Вынесенная валидация, общие утилиты
  - ❌ Плохо: Копипаст в 3+ местах

### Этап 3: Безопасность и бизнес-логика

- **Секреты**: Нет хардкода паролей/токенов?
  - ✅ Хорошо: `settings.jwt_secret_key`
  - ❌ Плохо: `"secret123"`, `"password"`

- **Валидация**: Входные данные проверяются?
  - ✅ Хорошо: Pydantic модели с `Field(...)`
  - ❌ Плохо: Без валидации входящих данных

- **Логирование**: Есть structlog?
  - ✅ Хорошо: `logger.info("action", user_id=user_id)`
  - ❌ Плохо: `print()` или отсутствие логов

### Этап 4: Тесты

- **Покрытие**: Новый код покрыт тестами?
  - ✅ Хорошо: Новый функционал имеет тесты
  - ❌ Плохо: Без тестов на новую логику

- **Маркировка**: unit vs integration разделены?
  - ✅ Хорошо: `@pytest.mark.unit` и `@pytest.mark.integration`
  - ❌ Плохо: Все тесты без маркеров

- **Именование тестов**: Описательное?
  - ✅ Хорошо: `test_login_with_invalid_key_raises_error`
  - ❌ Плохо: `test_1()`, `test_login()`

## Антипаттерны (отклонять)

| Антипаттерн | Пример | Проблема |
|-------------|--------|----------|
| Import * | `from app import *` | Неявные импорты |
| except pass | `except: pass` | Подавление ошибок |
| time.sleep async | `time.sleep(1)` | Блокировка event loop |
| Глобальные переменные | `GLOBAL_VAR = ...` | Race conditions |
| Длинные функции | >50 строк | Сложность |
| Magic numbers | `if x > 86400` | Непонятный код |
| Класс-бог | Класс на 500 строк | Single responsibility |

## Примеры Review

### ✅ Хороший код (Accept)

```python
# domain/services/token.py
from datetime import datetime, timezone
import jwt

class TokenDomainService:
    """Domain service for JWT token management."""

    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self._secret_key = secret_key
        self._algorithm = algorithm

    def create_token(
        self,
        service_name: str,
        expires_seconds: int = 86400,
    ) -> str:
        """Create JWT token for service."""
        now = int(datetime.now(timezone.utc).timestamp())
        payload = {
            "service": service_name,
            "exp": now + expires_seconds,
            "iat": now,
        }
        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)
```

**Принято, потому что:**
- Type hints на всех методах ✅
- Один метод — одно действие ✅
- DDD слой правильный (domain/services) ✅
- Константы понятны (86400 = 1 день) ✅
- Docstring есть ✅

### ❌ Плохой код (Request Changes)

```python
# utils.py
def create_token(service):
    import jwt
    now = datetime.now().timestamp()
    payload = {"service": service, "exp": now + 86400}
    return jwt.encode(payload, "secret123", algorithm="HS256")
```

**Отклонено, потому что:**
- Нет type hints ❌
- Хардкод секрета "secret123" ❌
- Не по DDD (utils.py) ❌
- Импорт внутри функции ❌
- Magic number 86400 ❌

### ❌ Плохой код (Request Changes)

```python
# api/routers/auth.py
@app.post("/login")
async def login(request: Request):
    data = await request.json()
    if not data.get("key"):
        return {"error": "no key"}
    token = jwt.encode({"service": "bot"}, "secret123")
    return {"token": token}
```

**Отклонено, потому что:**
- Логика в роутере (должна быть в domain/application) ❌
- Нет Pydantic модели для валидации ❌
- Хардкод "secret123" ❌
- Нет логирования ❌

## Workflow Review

1. **Pre-Review**: Запустить ruff, mypy, pytest
2. **Этап 1**: Проверить структуру и архитектуру
3. **Этап 2**: Проверить качество кода
4. **Этап 3**: Проверить безопасность и логику
5. **Этап 4**: Проверить тесты
6. **Финиш**: Написать комментарии (accept / request changes / discuss)

## Команды для проверки

```bash
# Линтер
ruff check .

# Форматирование
black --check .

# Типы
mypy src/backend

# Тесты
pytest -v --tb=short

# Все вместе (CI)
ruff check . && black --check . && mypy src/backend && pytest -v
```

## Ссылки

- Другие скиллы: `python-backend-developer`, `python-ddd-design`, `python-ddd-design`
- Docker: `docker-compose-dev`
- Bot: `bot-handlers`