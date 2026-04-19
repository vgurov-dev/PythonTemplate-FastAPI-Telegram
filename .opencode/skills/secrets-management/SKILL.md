---
name: secrets-management
description: Secrets management - .env, Docker secrets, CI secrets, rotation patterns
license: MIT
compatibility: opencode
metadata:
  audience: backend-developers, bot-developers, architects
  workflow: security
---

# Secrets Management Skill

## Role

Developer responsible for handling secrets securely. This skill covers how to manage credentials, tokens, and sensitive configuration across all environments without leaking them.

## Principles

### 1. Never commit secrets

- ❌ NEVER commit `.env` file
- ✅ Always commit `.env.example` with placeholder values
- ❌ NEVER hardcode secrets in code
- ✅ Use environment variables or Docker secrets

### 2. Secrets are environment-specific

- ✅ Different secrets for local, staging, production
- ❌ Same secret across all environments

### 3. Rotation without downtime

- ✅ Design for secret rotation
- ❌ Can't rotate without redeploy

## File Structure

```
project/
├── .env                    # Local secrets (NOT committed)
├── .env.example            # Template with placeholders (COMMITTED)
├── .gitignore             # Must include .env
└── docker-compose.yml      # Uses env_file, not embedded secrets
```

### .gitignore

```
# Environment files
.env
.env.local
.env.*.local

# Never commit these
*.pem
*.key
credentials.json
service-account.json
```

### .env.example (COMMITTED)

```bash
# ====================
# DATABASE
# ====================
DATABASE_URL=postgresql+asyncpg://user:CHANGEME@postgres:5432/myservice
POSTGRES_PASSWORD=CHANGEME  # Rotate in production

# ====================
# REDIS
# ====================
REDIS_PASSWORD=CHANGEME  # Rotate in production

# ====================
# JWT
# ====================
JWT_SECRET_KEY=CHANGEME  # CRITICAL: Rotate every 90 days
JWT_ALGORITHM=HS256

# ====================
# SERVICE AUTH
# ====================
SERVICE_KEY=CHANGEME  # Shared secret for bot↔backend

# ====================
# BOT
# ====================
BOT_TOKEN=CHANGEME  # Botfather token from @BotFather

# ====================
# MONITORING
# ====================
GRAFANA_PASSWORD=CHANGEME
PORTAINER_PASSWORD=CHANGEME

# ====================
# DEPLOYMENT (staging only)
# ====================
POSTGRES_PASSWORD_STAGING=CHANGEME
REDIS_PASSWORD_STAGING=CHANGEME
```

## Pydantic Settings Pattern

### Proper Configuration

```python
# backend/bootstrap/config.py
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database - no defaults for critical values
    database_url: str = Field(
        validation_alias="DATABASE_URL",
    )
    database_password: str = Field(
        validation_alias="DATABASE_PASSWORD",
    )

    # JWT - MUST be changed from default
    jwt_secret_key: str = Field(
        validation_alias="JWT_SECRET_KEY",
    )
    jwt_algorithm: str = Field(
        default="HS256",
        validation_alias="JWT_ALGORITHM",
    )

    # Service auth
    service_key: str = Field(
        validation_alias="SERVICE_KEY",
    )

    # Bot
    bot_token: str = Field(
        validation_alias="BOT_TOKEN",
    )

    # Optional with safe defaults
    log_level: str = Field(
        default="INFO",
        validation_alias="LOG_LEVEL",
    )
    app_debug: bool = Field(
        default=False,
        validation_alias="APP_DEBUG",
    )
```

### Validation at Startup

```python
# backend/bootstrap/config.py
import re

def validate_secrets() -> None:
    """Validate that secrets are not defaults."""
    dangerous_defaults = [
        ("JWT_SECRET_KEY", "your-secret-key-here"),
        ("SERVICE_KEY", "service-secret-key"),
        ("DATABASE_PASSWORD", "password"),
    ]

    for key, default_value in dangerous_defaults:
        current = getattr(settings, key.lower(), None)
        if current == default_value:
            raise ValueError(
                f"CRITICAL: {key} is still at default value! "
                f"Change it in production."
            )

# Call at module import
validate_secrets()
```

## Docker Secrets (Production)

### docker-compose.yml (Development)

```yaml
# Development - uses .env file
services:
  backend:
    env_file:
      - .env
```

### docker-compose.staging.yml (Production)

```yaml
# Production - uses Docker secrets
services:
  backend:
    secrets:
      - postgres_password
      - redis_password
      - jwt_secret_key
    environment:
      - DATABASE_URL=postgresql+asyncpg://user@postgres:5432/myservice
      - JWT_ALGORITHM=HS256
    env_file:
      - .env.no-secrets  # Non-sensitive config only

secrets:
  postgres_password:
    file: ./secrets/postgres_password.txt
  redis_password:
    file: ./secrets/redis_password.txt
  jwt_secret_key:
    file: ./secrets/jwt_secret_key.txt
```

### Secret Files

```bash
# secrets/postgres_password.txt
# Content: actual_postgres_password_here
# Permissions: chmod 600 secrets/postgres_password.txt
```

## CI/CD Secrets

### GitHub Actions Secrets

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      # Secrets are available via ${{ secrets.SECRET_NAME }}
      - name: Write secrets to .env
        run: |
          cat > .env << EOF
          DATABASE_URL=${{ secrets.DATABASE_URL }}
          POSTGRES_PASSWORD=${{ secrets.POSTGRES_PASSWORD }}
          REDIS_PASSWORD=${{ secrets.REDIS_PASSWORD }}
          JWT_SECRET_KEY=${{ secrets.JWT_SECRET_KEY }}
          SERVICE_KEY=${{ secrets.SERVICE_KEY }}
          BOT_TOKEN=${{ secrets.BOT_TOKEN }}
          GRAFANA_PASSWORD=${{ secrets.GRAFANA_PASSWORD }}
          PORTAINER_PASSWORD=${{ secrets.PORTAINER_PASSWORD }}
          SSH_HOST=${{ secrets.SSH_HOST }}
          SSH_USERNAME=${{ secrets.SSH_USERNAME }}
          SSH_PRIVATE_KEY=${{ secrets.SSH_PRIVATE_KEY }}
          EOF

      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.SSH_HOST }}
          username: ${{ secrets.SSH_USERNAME }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /app
            docker-compose pull
            docker-compose up -d
```

### Adding Secrets to GitHub

1. Go to Repository → Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. NEVER add secrets to code or commits

```
# NEVER DO THIS - secrets will be in git history
git commit -m "feat: add secrets"  # NO!
git push origin secret-branch       # NO!
```

## Secret Rotation

### Rotation Strategy

```python
# Rotation should NOT require code changes
# Design pattern: support both old and new secret during transition

class SecretRotation:
    """
    Strategy for rotating secrets without downtime.

    1. Generate new secret
    2. Deploy with support for BOTH old and new secret
    3. Update all clients to use new secret
    4. Remove old secret support
    """

    def __init__(self, old_secret: str, new_secret: str):
        self._old = old_secret
        self._new = new_secret

    def validate(self, token: str) -> bool:
        """Accept both old and new during transition."""
        return token in (self._old, self._new)

    def is_new(self, token: str) -> bool:
        """Check if this is the new secret."""
        return token == self._new
```

### JWT Rotation Without Downtime

```python
# backend/domain/services/token.py
class TokenDomainService:
    """
    Supports graceful JWT secret rotation.

    During transition period, accept tokens signed with either
    old or new secret. After all tokens are refreshed, only
    new secret is valid.
    """

    def __init__(
        self,
        primary_secret: str,
        fallback_secret: str | None = None,
        algorithm: str = "HS256",
    ):
        self._primary = primary_secret
        self._fallback = fallback_secret
        self._algorithm = algorithm

    def verify_token(self, token: str) -> TokenPayload:
        """Verify token with fallback support."""
        # Try primary first
        try:
            return self._verify_with_secret(token, self._primary)
        except JWTInvalidTokenError:
            # Try fallback if available
            if self._fallback:
                return self._verify_with_secret(token, self._fallback)
            raise
```

## Bot Token Security

### Safe Bot Configuration

```python
# bot/app/config.py
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
    )

    bot_token: str = Field(
        validation_alias="BOT_TOKEN",
    )

    # Bot should NOT know production database credentials
    # Only knows backend URL for API calls
    backend_url: str = Field(
        default="http://backend:8000",
        validation_alias="BACKEND_URL",
    )
```

### Never Log Tokens

```python
# BAD - token appears in logs
logger.info("bot_configured", token=settings.bot_token)

# GOOD - only log non-sensitive info
logger.info("bot_configured", token_prefix=settings.bot_token[:4] + "...")

# Also for errors
# BAD
raise ValueError(f"Invalid token: {token}")

# GOOD
raise ValueError("Invalid token")
```

## Service Key Patterns

### Bot → Backend Authentication

```python
# backend/bootstrap/config.py
class Settings(BaseSettings):
    # Service key for bot ↔ backend communication
    # Should be long and random, generated once
    service_key: str = Field(
        validation_alias="SERVICE_KEY",
    )

    # Token expiration for service tokens
    service_token_expire_seconds: int = Field(
        default=86400,
        validation_alias="SERVICE_TOKEN_EXPIRE_SECONDS",
    )
```

```python
# backend/api/routers/depends.py
from fastapi import Depends, HTTPException, Header

async def verify_service_token(
    authorization: str = Header(..., description="Bearer token"),
) -> str:
    """Verify service token for inter-service communication."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization[7:]

    # Constant-time comparison to prevent timing attacks
    import hmac
    if not hmac.compare_digest(token, settings.service_key):
        raise HTTPException(status_code=401, detail="Invalid service token")

    return token
```

## Anti-Patterns (NEVER do)

| Anti-pattern | Problem | Solution |
|-------------|---------|----------|
| Commit .env | Secrets in git history forever | Add to .gitignore |
| Hardcoded secrets | Leaked when code is public | Environment variables |
| Log tokens | Tokens in log aggregation | Mask tokens in logs |
| Same secret everywhere | One leak = all compromised | Unique per environment |
| No secret rotation | Old secrets never expire | Scheduled rotation |
| Secrets in URLs | May appear in logs, browser history | Use headers or body |
| Default values in code | Easy to forget to change | Fail at startup |
| Shared secrets | Can't revoke for one service | Per-service credentials |

## Security Checklist

- [ ] `.env` is in `.gitignore`
- [ ] `.env.example` has placeholder values, no real secrets
- [ ] All secrets use environment variables
- [ ] No default secrets in code (fail at startup)
- [ ] Docker secrets used in production
- [ ] GitHub Actions secrets configured for deploy
- [ ] Tokens are masked in logs
- [ ] Secrets are rotated periodically
- [ ] Fallback secrets support rotation without downtime
- [ ] Bot doesn't have database credentials

## Breach Response

If secrets are leaked:

1. **Immediately rotate** all exposed secrets
2. **Revoke old tokens** where possible
3. **Check git history** for what was exposed
4. **Review access logs** for misuse
5. **Enable additional monitoring** for affected services
6. **Document** the incident

```bash
# Emergency rotation script
#!/bin/bash
# Generate new secrets
NEW_JWT=$(openssl rand -hex 32)
NEW_SERVICE=$(openssl rand -hex 32)

# Update CI secrets via GitHub API
gh secret set JWT_SECRET_KEY --body "$NEW_JWT"
gh secret set SERVICE_KEY --body "$NEW_SERVICE"

# Deploy with new secrets
git tag -a v$(date +%Y%m%d%H%M%S) -m "Emergency secret rotation"
git push origin main --tags
```
