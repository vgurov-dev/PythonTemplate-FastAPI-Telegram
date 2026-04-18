---
name: docker-compose-dev
description: Docker Compose development workflow
license: MIT
compatibility: opencode
metadata:
  audience: maintainers
  workflow: devops
---

# Docker Compose Skill

## Rules

- Все сервисы запускать через docker-compose
- Не использовать poetry run напрямую для запуска
- Smoke test: docker-compose up -d + curl localhost:{port}/health
- Логи: docker-compose logs -f {service}
- Тесты: docker-compose exec {service} pytest
- Локальная разработка: docker-compose up --build