---
name: database-migrations
description: Alembic database migrations - creating, running, rolling back, zero-downtime patterns
license: MIT
compatibility: opencode
metadata:
  audience: backend-developers
  workflow: database
---

# Database Migrations Skill

## Role

Developer working with Alembic for database schema migrations. Covers creating migrations, running them safely, rolling back, and zero-downtime deployment patterns.

## Project Structure

```
src/backend/
├── alembic/
│   ├── env.py              # Alembic environment configuration
│   ├── script.py.mako      # Migration script template
│   └── versions/           # Migration scripts
│       ├── 001_initial.py
│       └── 002_add_user_email.py
├── infrastructure/
│   └── database/
│       └── models/         # SQLModel models
└── alembic.ini
```

## Alembic Configuration

### alembic.ini

```ini
[alembic]
script_location = alembic
prepend_sys_path = .
version_path_separator = os

sqlalchemy.url = driver://user:pass@localhost/dbname

[post_write_hooks]

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

### alembic/env.py

```python
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

from bootstrap.config import settings
from infrastructure.database.models import Base  # SQLModel models
from infrastructure.database.models.user import UserModel
from infrastructure.database.models.signup import SignupModel

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url():
    """Get database URL from app settings."""
    return settings.database_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with connection."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in async mode."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        url=get_url(),
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

## Creating Migrations

### autogenerate (preferred when possible)

```bash
# Generate migration from model changes
docker compose exec backend alembic revision --autogenerate -m "add users table"

# Or with specific connection
docker compose exec -e DATABASE_URL="..." backend alembic revision --autogenerate -m "add email column"
```

### Manual migration (when autogenerate isn't enough)

```bash
# Create empty migration
docker compose exec backend alembic revision -m "rename users to accounts"
```

### Migration File Structure

```python
# alembic/versions/003_add_user_email.py
"""add user email

Revision ID: 003_add_user_email
Revises: 002_initial_schema
Create Date: 2024-01-15 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import Column, Integer, String, DateTime, func

# revision identifiers
revision: str = '003_add_user_email'
down_revision: Union[str, None] = '002_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add email column to users table."""
    op.add_column(
        'users',
        Column('email', String(255), nullable=True, index=True)
    )


def downgrade() -> None:
    """Remove email column from users table."""
    op.drop_column('users', 'email')
```

## Running Migrations

### Development

```bash
# Run all migrations
docker compose exec backend alembic upgrade head

# Run next migration
docker compose exec backend alembic upgrade +1

# Check current version
docker compose exec backend alembic current

# Show migration history
docker compose exec backend alembic history --verbose

# Show pending migrations
docker compose exec backend alembic heads
```

### Production (with care)

```bash
# Always check what will run FIRST
docker compose exec backend alembic upgrade head --sql > migration.sql
# Review the SQL before running!

# Then run if OK
docker compose exec backend alembic upgrade head
```

### Dry run

```bash
# Show what would be applied without applying
docker compose exec backend alembic upgrade head --dry-run
```

## Rolling Back

### Basic rollback

```bash
# Rollback last migration
docker compose exec backend alembic downgrade -1

# Rollback to specific revision
docker compose exec backend alembic downgrade 001_initial

# Rollback to base (empty database)
docker compose exec backend alembic downgrade base
```

### Rollback with data loss warning

```bash
# For destructive operations, always verify first
docker compose exec backend alembic downgrade -1 --sql > rollback.sql
# Review the SQL carefully!

# Check if there's data that will be lost
docker compose exec postgres psql -U user -d myservice -c "SELECT COUNT(*) FROM table_name;"
```

## Zero-Downtime Patterns

### Adding a Column (Safe)

```python
# 1. Add column as nullable (no default if table is large)
def upgrade() -> None:
    op.add_column(
        'users',
        Column('nickname', String(100), nullable=True)
    )

def downgrade() -> None:
    op.drop_column('users', 'nickname')
```

```python
# 2. Backfill data in separate migration
def upgrade() -> None:
    # No changes to schema
    pass

def downgrade() -> None:
    pass

# In a separate Python script or migration
async def backfill_nicknames():
    from infrastructure.database.repositories.user import UserRepository
    from bootstrap.database import async_session_factory

    async with async_session_factory() as session:
        repo = UserRepository(session)
        await repo.backfill_nicknames()
```

```python
# 3. Add NOT NULL constraint after backfill
def upgrade() -> None:
    op.alter_column('users', 'nickname', nullable=False)

def downgrade() -> None:
    op.alter_column('users', 'nickname', nullable=True)
```

### Renaming a Column (Expand-Contract)

```python
# Step 1: Add new column (expand)
def upgrade() -> None:
    op.add_column(
        'users',
        Column('username_new', String(100), nullable=True)
    )

def downgrade() -> None:
    op.drop_column('users', 'username_new')

# Step 2: Backfill data
# ... separate script ...

# Step 3: Make NOT NULL, rename (contract)
def upgrade() -> None:
    op.alter_column('users', 'username_new', nullable=False)
    op.execute("ALTER TABLE users RENAME COLUMN username TO username_old")
    op.execute("ALTER TABLE users RENAME COLUMN username_new TO username")

def downgrade() -> None:
    op.execute("ALTER TABLE users RENAME COLUMN username TO username_new")
    op.execute("ALTER TABLE users RENAME COLUMN username_old TO username")
    op.alter_column('users', 'username_new', nullable=True)
```

### Adding an Index (Online)

```python
# Use CREATE INDEX CONCURRENTLY in PostgreSQL
def upgrade() -> None:
    op.create_index(
        'ix_users_email',
        'users',
        ['email'],
        unique=False,
        if_not_exists=True,
        postgresql_concurrently=True,  # Non-locking!
    )

def downgrade() -> None:
    op.drop_index(
        'ix_users_email',
        'users',
        if_exists=True,
        postgresql_concurrently=True,
    )
```

### Adding a Table (Safe)

```python
def upgrade() -> None:
    op.create_table(
        'user_sessions',
        Column('id', Integer, primary_key=True),
        Column('user_id', Integer, nullable=False),
        Column('token_hash', String(255), nullable=False),
        Column('expires_at', DateTime, nullable=False),
        Column('created_at', DateTime, server_default=func.now()),
    )
    op.create_index('ix_user_sessions_user_id', 'user_sessions', ['user_id'])
    op.create_index('ix_user_sessions_expires', 'user_sessions', ['expires_at'])

def downgrade() -> None:
    op.drop_table('user_sessions')
```

### Dropping a Table (Danger - never in production without backup)

```python
# NEVER drop tables without:
# 1. Ensuring no application code uses them
# 2. Taking a backup
# 3. Having a rollback plan

def upgrade() -> None:
    op.drop_table('old_backup_table')

def downgrade() -> None:
    op.create_table('old_backup_table', ...)
```

## Data Migrations

### Async Data Migration Script

```python
# alembic/versions/004_backfill_user_emails.py
"""backfill user emails

Revision ID: 004_backfill_user_emails
Revises: 003_add_user_email
Create Date: 2024-01-16 10:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '004_backfill_user_emails'
down_revision: Union[str, None] = '003_add_user_email'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No schema changes - data only."""
    pass


def downgrade() -> None:
    """No rollback for data migration."""
    pass


# Run this separately after migration
async def backfill():
    """Backfill email from username where email is null."""
    from infrastructure.database.repositories.user import UserRepository
    from bootstrap.database import async_session_factory

    async with async_session_factory() as session:
        repo = UserRepository(session)
        await repo.backfill_email_from_username()
```

### Synchronous Data Migration

```python
# For simpler cases, within the migration itself
def upgrade() -> None:
    # First add column (see above)
    op.add_column('users', Column('email', String(255), nullable=True))

    # Then backfill
    op.execute("""
        UPDATE users
        SET email = username || '@example.com'
        WHERE email IS NULL
    """)

    # Then make NOT NULL
    op.alter_column('users', 'email', nullable=False)
```

## SQLModel Models

```python
# infrastructure/database/models/user.py
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlmodel import SQLModel, Field

from infrastructure.database.models.base import Base


class UserModel(SQLModel, Base):
    """User database model."""

    __tablename__ = "users"

    id: Optional[int] = Field(default=None, sa_column=Column(Integer, primary_key=True))
    telegram_id: int = Field(sa_column=Column(Integer, unique=True, index=True, nullable=False))
    username: Optional[str] = Field(sa_column=Column(String(100), nullable=True))
    first_name: str = Field(sa_column=Column(String(100), nullable=False))
    email: Optional[str] = Field(sa_column=Column(String(255), nullable=True, index=True))
    created_at: datetime = Field(
        sa_column=Column(DateTime, server_default=func.now(), nullable=False)
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    )
```

## Testing Migrations

```python
# backend/tests/integration/test_migrations.py
import pytest
from alembic.config import Config
from alembic import command
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text

from bootstrap.config import settings


@pytest.fixture
def alembic_config():
    """Get Alembic configuration."""
    return Config("alembic.ini")


@pytest.fixture
def alembic_script(alembic_config):
    """Get Alembic script directory."""
    return ScriptDirectory.from_config(alembic_config)


@pytest.mark.integration
def test_all_migrations_can_run_and_rollback(alembic_config, tmp_path):
    """Test that all migrations can run and rollback successfully."""
    # Create test database
    test_db_url = f"{settings.database_url}_test"

    # Run migrations
    command.upgrade(alembic_config, 'head')

    # Verify tables exist
    engine = create_engine(test_db_url)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        assert result.scalar() == 1

    # Rollback
    command.downgrade(alembic_config, 'base')

    # Verify tables dropped
    with engine.connect() as conn:
        # Should fail or return empty
        result = conn.execute(text("SELECT COUNT(*) FROM users"))
        # ...

    engine.dispose()


@pytest.mark.integration
def test_migration_order(alembic_script):
    """Test that migrations are properly ordered."""
    revisions = [rev.revision for rev in alembic_script.walk_revisions()]

    # Verify no branching
    assert len(revisions) == len(set(revisions)), "Migration tree has branches!"

    # Verify linear history
    for i, rev in enumerate(revisions[:-1]):
        next_rev = alembic_script.get_next(rev)
        assert next_rev == revisions[i + 1]
```

## Anti-Patterns (NEVER do)

| Anti-pattern | Problem | Solution |
|-------------|---------|----------|
| NOT NULL without backfill | Data loss | Add column nullable, backfill, then alter |
| Drop column without verification | Broken application | Ensure no code uses it |
| Destructive migrations in prod | Data loss | Always backup first |
| Rename column directly | Locks table, breaks app | Expand-contract pattern |
| Non-concurrent index on large table | Table lock | Use postgresql_concurrently=True |
| Edit old migrations | Breaks migration history | Create new migration instead |
| No migration testing | Untested schema changes | Test both upgrade and downgrade |

## Checklist

Before running migrations:

- [ ] Migrations are reviewed (not just autogenerated)
- [ ] No destructive operations without backup
- [ ] Large table alterations use expand-contract
- [ ] Indexes use CONCURRENTLY in PostgreSQL
- [ ] Rollback plan is documented
- [ ] No application code depends on old schema
- [ ] Tested on staging first
- [ ] Zero-downtime patterns used for critical tables
