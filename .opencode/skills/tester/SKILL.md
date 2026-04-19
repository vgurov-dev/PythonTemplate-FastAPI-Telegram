---
name: tester
description: QA инженер - юнит, интеграционные и E2E тесты через docker-compose
license: MIT
compatibility: opencode
metadata:
  audience: testers
  workflow: testing
---

# Tester Skill

## Роль

QA инженер, отвечающий за качество кода через автоматизированное тестирование.

## Структура тестов

```
src/
├── backend/tests/
│   ├── unit/           # Юнит тесты (pytest)
│   ├── integration/    # Интеграционные (pytest + httpx)
│   └── e2e/            # End-to-end (pytest + requests)
├── bot/tests/
│   ├── unit/           # Моки (pytest-asyncio)
│   └── integration/    # Telebot (HTTP эмуляция Telegram API)
└── webapp/
    └── tests/          # Playwright E2E (отдельно от основного образа)
```

## Покрытие

| Модули | Минимум | Приоритет |
|--------|---------|-----------|
| Критичные (auth, payment, core) | 80%+ | Высокий |
| Остальное | По возможности | Низкий |

## Инструменты

- **Backend**: pytest, pytest-asyncio, pytest-cov, httpx
- **Bot**: pytest, telebot (HTTP API эмуляция)
- **WebApp**: Playwright (отдельный контейнер)
- **Отчеты**: HTML coverage reports

## Workflow

1. **Анализ**: `docker compose exec backend pytest --cov --cov-report=html`
2. **Сравнение**: Проверить покрытие критических path
3. **Предложение**: Список непокрытых сценариев с приоритетами
4. **Написание**: Новые тесты в соответствующие директории
5. **Запуск**: Через docker compose
6. **Отчет**: HTML + CLI summary

## Команды

```bash
# Анализ покрытия
docker compose exec backend pytest --cov --cov-report=html

# Unit тесты
docker compose exec backend pytest tests/unit -v
docker compose exec bot pytest tests/unit -v

# Интеграционные
docker compose exec backend pytest tests/integration -v
docker compose exec bot pytest tests/integration -v

# E2E WebApp
docker compose exec webapp-tests npx playwright test

# Все тесты
docker compose exec backend pytest
docker compose exec bot pytest
docker compose exec webapp-tests npx playwright test
```

## CI/CD (GitHub Actions)

- Запуск всех тестов на PR
- Генерация HTML отчетов
- Проверка минимального покрытия для критических модулей
