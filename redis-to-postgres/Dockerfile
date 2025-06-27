# ===========================
# 1. Build Stage (Alpine)
# ===========================
FROM python:3.12-alpine AS builder

ENV POETRY_VERSION=2.1.3

RUN apk add --no-cache \
    build-base \
    libffi-dev \
    py3-pip \
    curl \
    openssl-dev

RUN pip install "poetry==$POETRY_VERSION"

WORKDIR /app

COPY pyproject.toml poetry.lock README.md /app/
RUN poetry config virtualenvs.create false && \
    poetry install --no-root

COPY src/ /app/src/
COPY config/ /app/config/
RUN poetry build -f wheel

# ===========================
# 2. Runtime Stage (Alpine)
# ===========================
FROM python:3.12-alpine AS runtime

WORKDIR /app

RUN apk add --no-cache \
    libffi \
    openssl

COPY --from=builder /app/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl

COPY config/ /app/config/

# Entrypoint: poetry script로 등록된 redis-to-postgres 사용
CMD ["redis-to-postgres", "--config", "config/config.toml", "--log-config", "config/logger.toml"]