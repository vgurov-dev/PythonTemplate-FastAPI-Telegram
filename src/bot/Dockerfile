FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install poetry && poetry config virtualenvs.create false && poetry install --no-interaction --with bot

COPY src/bot/ ./src/bot/
WORKDIR /app/src/bot

CMD ["python", "-m", "bot.main"]