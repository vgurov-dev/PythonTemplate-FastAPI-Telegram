FROM python:3.12-slim

# Create non-root user
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install poetry && poetry config virtualenvs.create false && poetry install --no-interaction --no-root

COPY --chown=appuser:appgroup src/backend/ /app/

ENV PYTHONPATH=/app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "bootstrap.main:app", "--host", "0.0.0.0", "--port", "8000"]
