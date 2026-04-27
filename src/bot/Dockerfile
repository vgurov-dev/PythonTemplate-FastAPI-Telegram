FROM python:3.12-slim

# Create non-root user
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install poetry && poetry config virtualenvs.create false && poetry install --no-interaction --with bot --no-root

COPY --chown=appuser:appgroup src/bot/ ./src/bot/

ENV PYTHONPATH=/app/src/bot
USER appuser

CMD ["python", "-m", "bot.main"]
