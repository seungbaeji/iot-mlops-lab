# redis-to-postgres

This service consumes sensor data from a Redis queue and batch-inserts it into PostgreSQL.

## Features
- Async, efficient batch processing
- Configurable via `config/config.toml`
- Designed for production IoT/ML pipelines

## Configuration
See `config/config.toml` for Redis, Postgres, and worker settings.

## Usage

```bash
poetry install
poetry run python -m redis_to_postgres.main
```

## Observability
- Add OpenTelemetry, logging, and metrics as needed for production.

## Table Schema
You must create the following table in your Postgres DB:

```sql
CREATE TABLE sensor_data (
    device_id TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    value DOUBLE PRECISION NOT NULL
);
```
```

---

필요한 파일을 모두 복사해서 붙여넣으시면 됩니다!  
추가로 궁금한 점이나, 다른 서비스/문서화 작업도 필요하시면 말씀해 주세요.