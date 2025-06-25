# ===========================
# 1. Build Stage (Alpine)
# ===========================
FROM python:3.12-alpine AS builder

ENV POETRY_VERSION=2.1.3

# 필수 패키지 설치 (poetry 빌드에 필요한 의존성 포함)
RUN apk add --no-cache \
    build-base \
    libffi-dev \
    py3-pip \
    curl \
    openssl-dev

# Poetry 설치
RUN pip install "poetry==$POETRY_VERSION"

WORKDIR /app

# pyproject.toml과 lock 파일 복사
COPY pyproject.toml poetry.lock /app/

# Poetry 설정 및 의존성 설치
RUN poetry config virtualenvs.create false && \
    poetry install --no-root

# 소스 코드 복사 및 wheel 빌드
COPY src/ /app/src/
RUN poetry build -f wheel


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
RUN pip install --no-cache-dir /tmp/*.whl

# 앱 실행
CMD ["subsrciber", "--config", "config/config.toml", "--log-config", "config/logger.toml"]
