# ===========================
# 1. Build Stage (Alpine)
# ===========================
FROM python:3.12-alpine AS builder

RUN apk add --no-cache \
    build-base \
    libffi-dev \
    openssl-dev \
    curl \
    git \
    py3-pip

# uv 설치
RUN pip install uv

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src/ ./src/

# wheel 빌드
RUN uv build --wheel

# ===========================
# 2. Runtime Stage (Alpine)
# ===========================
FROM python:3.12-alpine AS runtime

WORKDIR /app

RUN apk add --no-cache \
    libffi \
    openssl

COPY --from=builder /app/dist/*.whl /tmp/
COPY pip.conf /root/.pip/pip.conf
RUN pip install --no-cache-dir /tmp/*.whl

COPY config/ /app/config/

CMD ["redis-to-postgres", "--config", "config/config.toml", "--log-config", "config/logger.toml"]
