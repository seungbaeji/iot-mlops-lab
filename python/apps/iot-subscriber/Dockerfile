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

# 런타임에 필요한 최소 패키지
RUN apk add --no-cache \
    libffi \
    openssl

# 빌드된 wheel 파일 복사 및 설치
COPY --from=builder /app/dist/*.whl /tmp/
COPY pip.conf /root/.pip/pip.conf
RUN pip install --no-cache-dir /tmp/*.whl

# 앱 실행
CMD ["iot-subsrciber", "--config", "config/config.toml", "--log-config", "config/logger.toml"]
