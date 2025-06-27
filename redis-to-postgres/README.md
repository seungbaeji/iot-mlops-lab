# Redis to Postgres Worker

## Overview

**redis-to-postgres** is a service that reads data from a Redis queue/stream and writes it to a PostgreSQL database. It is designed to be a downstream consumer in a decoupled data pipeline, enabling scalable and reliable ingestion of IoT or other event data. **Multiple redis-to-postgres workers can run in parallel for higher throughput and fault tolerance.**

## Architecture

```
+-----------+      +-----------+      +----------------------+
|  MQTT     | ---> |  Redis    | ---> | redis-to-postgres    |
|  Broker   |      |  (Queue)  |      |   (one or more)      |
+-----------+      +-----------+      +----------------------+
                                         |
                                         v
                                 +------------------+
                                 |   PostgreSQL     |
                                 +------------------+
```

- **Redis**: Buffers incoming data from upstream producers (e.g., MQTT subscriber) and supports multiple consumers (e.g., via consumer groups or streams)
- **redis-to-postgres (this service)**: One or more worker instances can read batches from Redis and insert them into PostgreSQL concurrently
- **PostgreSQL**: Stores the data for analytics, reporting, or further processing

## Why this pattern?

- **Decoupling**: Ingestion and storage are separated, so each can scale and fail independently
- **Reliability**: Data is buffered in Redis, preventing loss if PostgreSQL is temporarily unavailable
- **Extensibility**: Additional consumers (e.g., for preprocessing, analytics) can be added without changing this service
- **Scalability**: Multiple redis-to-postgres workers can run in parallel to increase throughput and provide redundancy

## Getting Started

1. Configure Redis and PostgreSQL settings in `config.toml`.
2. Start one or more redis-to-postgres service instances.
3. Ensure that upstream producers (e.g., MQTT subscriber) are pushing data to Redis.

---

**Note:**
- This service does **not** ingest data from MQTT or other sources directly. It only processes data from Redis and writes to PostgreSQL.
- For MQTT ingestion, use a separate service (e.g., IoT Subscriber).
- You can run multiple redis-to-postgres workers in parallel for higher throughput and fault tolerance.

For more details, see the code and configuration files in this repository.

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