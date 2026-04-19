---
name: ci-cd-pipeline
description: CI/CD pipeline - GitHub Actions workflows, Docker builds, deployment, rollback
license: MIT
compatibility: opencode
metadata:
  audience: developers, devops
  workflow: ci-cd
---

# CI/CD Pipeline Skill

## Role

Developer or DevOps working with CI/CD pipelines. Covers GitHub Actions workflows, Docker image builds, multi-arch builds, and deployment strategies.

## Project Structure

```
.github/
├── workflows/
│   ├── ci.yml          # Continuous Integration
│   └── cd.yml          # Continuous Deployment
└── actions/
    └── ...
```

## CI Pipeline (ci.yml)

### Full CI Workflow

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, dev]
  pull_request:
    branches: [main, dev]

jobs:
  lint-backend:
    name: Lint Backend
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'poetry'

      - name: Install Poetry
        run: pip install poetry

      - name: Install dependencies
        run: poetry install --with backend

      - name: Run Ruff linter
        run: poetry run ruff check src/backend/
        continue-on-error: false

      - name: Run Black formatter check
        run: poetry run black --check src/backend/
        continue-on-error: false

      - name: Run type check
        run: poetry run mypy src/backend/
        continue-on-error: false

  test-backend:
    name: Test Backend
    runs-on: ubuntu-latest
    needs: lint-backend
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: user
          POSTGRES_PASSWORD: password
          POSTGRES_DB: testdb
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'poetry'

      - name: Install Poetry
        run: pip install poetry

      - name: Install dependencies
        run: poetry install --with backend,dev

      - name: Run backend tests
        run: poetry run pytest src/backend/tests/ -v --cov=src/backend --cov-report=xml
        env:
          DATABASE_URL: postgresql+asyncpg://user:password@localhost:5432/testdb
          REDIS_URL: redis://localhost:6379/0

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage.xml
          fail_ci_if_error: true

  lint-bot:
    name: Lint Bot
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'poetry'

      - name: Install Poetry
        run: pip install poetry

      - name: Install dependencies
        run: poetry install --with bot

      - name: Run Ruff linter
        run: poetry run ruff check src/bot/
        continue-on-error: false

  lint-webapp:
    name: Lint WebApp
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: src/webapp/package-lock.json

      - name: Install dependencies
        run: npm ci
        working-directory: src/webapp

      - name: Run ESLint
        run: npm run lint
        working-directory: src/webapp

      - name: Build webapp
        run: npm run build
        working-directory: src/webapp
        continue-on-error: false

  docker-build:
    name: Docker Build
    runs-on: ubuntu-latest
    needs: [lint-backend, test-backend, lint-bot, lint-webapp]
    if: github.event_name == 'push'
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build backend
        uses: docker/build-push-action@v6
        with:
          context: .
          file: src/backend/Dockerfile
          push: false
          tags: |
            my-service/backend:${{ github.sha }}
            my-service/backend:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max
          platforms: linux/amd64,linux/arm64

      - name: Build bot
        uses: docker/build-push-action@v6
        with:
          context: .
          file: src/bot/Dockerfile
          push: false
          tags: |
            my-service/bot:${{ github.sha }}
            my-service/bot:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max
          platforms: linux/amd64,linux/arm64

      - name: Build webapp
        uses: docker/build-push-action@v6
        with:
          context: ./src/webapp
          file: src/webapp/Dockerfile
          push: false
          tags: |
            my-service/webapp:${{ github.sha }}
            my-service/webapp:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max
          platforms: linux/amd64,linux/arm64
```

## CD Pipeline (cd.yml)

### Full CD Workflow

```yaml
# .github/workflows/cd.yml
name: CD

on:
  push:
    branches: [main]
    tags:
      - 'v*'
  workflow_dispatch:
    inputs:
      environment:
        description: 'Environment to deploy'
        required: true
        default: 'staging'
        type: choice
        options:
          - staging
          - production

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build-and-push:
    name: Build and Push Images
    runs-on: ubuntu-latest
    outputs:
      backend-tag: ${{ steps.meta.outputs.backend-tag }}
      bot-tag: ${{ steps.meta.outputs.bot-tag }}
      webapp-tag: ${{ steps.meta.outputs.webapp-tag }}
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: |
            ${{ env.REGISTRY }}/${{ github.repository }}/backend
            ${{ env.REGISTRY }}/${{ github.repository }}/bot
            ${{ env.REGISTRY }}/${{ github.repository }}/webapp
          tags: |
            type=ref,event=branch
            type=sha,prefix=
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=raw,value=latest,enable={{is_default_branch}}

      - name: Set image tags output
        id: tags
        run: |
          echo "backend-tag=$(echo '${{ steps.meta.outputs.backend-tags }}' | tr ' ' '\n' | grep backend | head -1)" >> $GITHUB_OUTPUT
          echo "bot-tag=$(echo '${{ steps.meta.outputs.bot-tags }}' | tr ' ' '\n' | grep bot | head -1)" >> $GITHUB_OUTPUT
          echo "webapp-tag=$(echo '${{ steps.meta.outputs.webapp-tags }}' | tr ' ' '\n' | grep webapp | head -1)" >> $GITHUB_OUTPUT

      - name: Build and push backend
        uses: docker/build-push-action@v6
        with:
          context: .
          file: src/backend/Dockerfile
          push: true
          tags: ${{ fromJSON(steps.meta.outputs.json).backend.tags }}
          labels: ${{ fromJSON(steps.meta.outputs.json).backend.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
          platforms: linux/amd64,linux/arm64

      - name: Build and push bot
        uses: docker/build-push-action@v6
        with:
          context: .
          file: src/bot/Dockerfile
          push: true
          tags: ${{ fromJSON(steps.meta.outputs.json).bot.tags }}
          labels: ${{ fromJSON(steps.meta.outputs.json).bot.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
          platforms: linux/amd64,linux/arm64

      - name: Build and push webapp
        uses: docker/build-push-action@v6
        with:
          context: ./src/webapp
          file: src/webapp/Dockerfile
          push: true
          tags: ${{ fromJSON(steps.meta.outputs.json).webapp.tags }}
          labels: ${{ fromJSON(steps.meta.outputs.json).webapp.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
          platforms: linux/amd64,linux/arm64

  deploy-staging:
    name: Deploy to Staging
    runs-on: ubuntu-latest
    needs: build-and-push
    if: github.ref == 'refs/heads/main' || github.event_name == 'workflow_dispatch'
    environment:
      name: staging
      url: https://staging.example.com
    steps:
      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.SSH_HOST_STAGING }}
          username: ${{ secrets.SSH_USERNAME_STAGING }}
          key: ${{ secrets.SSH_PRIVATE_KEY_STAGING }}
          envs: GITHUB_SHA
          script: |
            cd /app
            export TAG=${{ github.sha }}
            export BACKEND_IMAGE=${{ env.REGISTRY }}/${{ github.repository }}/backend:${{ github.sha }}
            export BOT_IMAGE=${{ env.REGISTRY }}/${{ github.repository }}/bot:${{ github.sha }}
            export WEBAPP_IMAGE=${{ env.REGISTRY }}/${{ github.repository }}/webapp:${{ github.sha }}

            # Pull new images
            docker-compose -f docker-compose.staging.yml pull

            # Update images in compose
            BACKEND_IMAGE=$BACKEND_IMAGE BOT_IMAGE=$BOT_IMAGE WEBAPP_IMAGE=$WEBAPP_IMAGE \
              docker-compose -f docker-compose.staging.yml up -d

            # Cleanup
            docker system prune -f || true

  deploy-production:
    name: Deploy to Production
    runs-on: ubuntu-latest
    needs: build-and-push
    if: startsWith(github.ref, 'refs/tags/v')
    environment:
      name: production
      url: https://example.com
    steps:
      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.SSH_HOST_PRODUCTION }}
          username: ${{ secrets.SSH_USERNAME_PRODUCTION }}
          key: ${{ secrets.SSH_PRIVATE_KEY_PRODUCTION }}
          envs: GITHUB_SHA
          script: |
            cd /app
            export TAG=${{ github.ref_name }}
            export BACKEND_IMAGE=${{ env.REGISTRY }}/${{ github.repository }}/backend:${{ github.ref_name }}
            export BOT_IMAGE=${{ env.REGISTRY }}/${{ github.repository }}/bot:${{ github.ref_name }}
            export WEBAPP_IMAGE=${{ env.REGISTRY }}/${{ github.repository }}/webapp:${{ github.ref_name }}

            # Backup database before deployment
            ./scripts/backup-db.sh || true

            # Pull and deploy
            docker-compose -f docker-compose.production.yml pull
            BACKEND_IMAGE=$BACKEND_IMAGE BOT_IMAGE=$BOT_IMAGE WEBAPP_IMAGE=$WEBAPP_IMAGE \
              docker-compose -f docker-compose.production.yml up -d

            # Health check
            ./scripts/health-check.sh || {
              echo "Health check failed, rolling back..."
              git revert HEAD --no-commit
              docker-compose -f docker-compose.production.yml up -d
              exit 1
            }
```

## Docker Tagging Strategy

### GitHub Actions Metadata

| Event | Tag Pattern | Example |
|-------|-------------|---------|
| Push to main | `latest` | `ghcr.io/org/backend:latest` |
| Push to dev | `dev-{sha}` | `ghcr.io/org/backend:dev-a1b2c3d` |
| Tag v1.2.3 | `1.2.3`, `1.2`, `latest` | `ghcr.io/org/backend:1.2.3` |
| PR | `pr-{number}` | `ghcr.io/org/backend:pr-123` |

### Image References

```bash
# Docker Compose staging
BACKEND_IMAGE=ghcr.io/vgurov-dev/telegram-template/backend:${TAG:-latest}

# In docker-compose.staging.yml
services:
  backend:
    image: ghcr.io/vgurov-dev/telegram-template/backend:${TAG:-latest}
```

## Multi-Arch Builds

### Buildx Configuration

```yaml
# Build for multiple architectures
- name: Build and push
  uses: docker/build-push-action@v6
  with:
    context: .
    file: src/backend/Dockerfile
    push: true
    platforms: |
      linux/amd64
      linux/arm64
      linux/arm/v7
    tags: |
      my-service/backend:latest
      my-service/backend:${{ github.sha }}
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

## GitHub Secrets

### Required Secrets

| Secret | Description |
|--------|-------------|
| `GITHUB_TOKEN` | Built-in, available automatically |
| `SSH_HOST_STAGING` | Staging server hostname |
| `SSH_USERNAME_STAGING` | Staging SSH username |
| `SSH_PRIVATE_KEY_STAGING` | Staging SSH private key |
| `SSH_HOST_PRODUCTION` | Production server hostname |
| `SSH_USERNAME_PRODUCTION` | Production SSH username |
| `SSH_PRIVATE_KEY_PRODUCTION` | Production SSH private key |
| `DOCKERHUB_USERNAME` | Docker Hub username (if using Docker Hub) |
| `DOCKERHUB_TOKEN` | Docker Hub access token |

### Adding Secrets

1. Go to Repository → Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. NEVER add secrets to code

## Rollback Strategy

### Git-based Rollback

```bash
# Rollback to previous tag
git checkout v1.2.2
git tag -f production
git push origin production --force

# Or via GitHub UI:
# 1. Go to Actions
# 2. Find successful deployment
# 3. Click "Re-run jobs"
```

### Docker-based Rollback

```bash
# On server, find previous image
docker images | grep backend

# Pull specific tag
BACKEND_IMAGE=ghcr.io/org/backend:v1.2.2 \
docker-compose -f docker-compose.production.yml up -d backend

# Or use specific SHA
docker pull ghcr.io/org/backend@sha256:abc123...
```

### Rollback Script

```bash
#!/bin/bash
# scripts/rollback.sh

PREVIOUS_TAG=${1:-$(git describe --tags --abbrev=0 HEAD^)}
export TAG=$PREVIOUS_TAG

echo "Rolling back to $PREVIOUS_TAG"

export BACKEND_IMAGE=$REGISTRY/backend:$PREVIOUS_TAG
export BOT_IMAGE=$REGISTRY/bot:$PREVIOUS_TAG
export WEBAPP_IMAGE=$REGISTRY/webapp:$PREVIOUS_TAG

docker-compose -f docker-compose.production.yml pull
docker-compose -f docker-compose.production.yml up -d

echo "Rolled back to $PREVIOUS_TAG"
```

## Adding New Jobs

### Adding a New Service

```yaml
# Add lint for new service
lint-new-service:
  name: Lint New Service
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.12'

    - name: Install Poetry
      run: pip install poetry

    - name: Install dependencies
      run: poetry install --with new-service

    - name: Run linter
      run: poetry run ruff check src/new-service/

# Update docker-build needs
docker-build:
  needs: [lint-backend, test-backend, lint-bot, lint-webapp, lint-new-service]

# Add build step for new service
- name: Build new-service
  uses: docker/build-push-action@v6
  with:
    context: .
    file: src/new-service/Dockerfile
    push: true
    tags: |
      my-service/new-service:${{ github.sha }}
      my-service/new-service:latest
```

## Conditional Execution

### Skip CI for Certain Changes

```yaml
# Skip CI for docs only changes
on:
  push:
    paths:
      - 'docs/**'
      - '**.md'
      - '.gitignore'
      - 'LICENSE'

jobs:
  lint-backend:
    if: "!(contains(github.event.head_commit.message, '[skip ci]'))"
    # ...
```

### Branch-based Conditions

```yaml
jobs:
  deploy-staging:
    if: github.ref == 'refs/heads/main'

  deploy-production:
    if: startsWith(github.ref, 'refs/tags/v')
```

## Caching

### Poetry Cache

```yaml
- name: Install Poetry
  run: pip install poetry

- name: Set up Python
  uses: actions/setup-python@v5
  with:
    python-version: '3.12'
    cache: 'poetry'
```

### Docker Cache

```yaml
- name: Build and push
  uses: docker/build-push-action@v6
  with:
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

## Health Checks

```bash
#!/bin/bash
# scripts/health-check.sh

MAX_RETRIES=30
RETRY_INTERVAL=2

for i in $(seq 1 $MAX_RETRIES); do
  if curl -sf http://localhost:8000/health > /dev/null; then
    echo "Health check passed"
    exit 0
  fi
  echo "Waiting for service... ($i/$MAX_RETRIES)"
  sleep $RETRY_INTERVAL
done

echo "Health check failed"
exit 1
```

## Anti-Patterns (NEVER do)

| Anti-pattern | Problem | Solution |
|-------------|---------|----------|
| No tests in CI | Broken code deployed | Add test job |
| Push without lint | Style violations in prod | Lint before build |
| Deploy without staging | Untested in staging | Always deploy to staging first |
| Hardcoded secrets | Exposed in history | Use GitHub Secrets |
| No rollback plan | Can't recover | Document rollback procedure |
| Build only on main | PRs not tested | Build on PRs too |
| Missing cache | Slow builds | Configure caching |
| Deploy from local | Not reproducible | CI/CD only |

## Checklist

Before deploying:

- [ ] All CI jobs passed
- [ ] Staging deployment successful
- [ ] Health checks pass
- [ ] Logs are being collected
- [ ] Rollback procedure documented
- [ ] Team notified of deployment
- [ ] Secrets configured in GitHub
