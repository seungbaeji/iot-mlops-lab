# IoT Subscriber

## Overview

**IoT Subscriber** is a service that ingests data from an MQTT broker and pushes it to a Redis queue. Its sole responsibility is to reliably transfer incoming MQTT messages to Redis for further processing. All downstream processing (such as database storage, analytics, or preprocessing) is handled by separate services and is not part of this module.

## Architecture

```
+-----------+      +-----------+
|  MQTT     | ---> |  Redis    |
|  Broker   |      |  (Queue)  |
+-----------+      +-----------+
                        |
                        v
                [Downstream Consumers]
                (e.g. Postgres, Preprocessing, Analytics)
                (Not part of this service)
```

- **MQTT Subscriber (this service)**: Receives messages from MQTT and pushes them to Redis.
- **Redis**: Acts as a buffer/queue, enabling multiple independent downstream consumers.
- **Downstream Consumers**: Separate services that read from Redis and perform further processing (not included here).

## Why Redis?

- **Scalability**: Multiple consumers can process data in parallel.
- **Extensibility**: New pipelines (e.g., preprocessing, ML, analytics) can be added without changing the MQTT subscriber.
- **Fault Tolerance**: If a downstream service is down, data is safely buffered in Redis.
- **Decoupling**: Ingestion and processing are separated, making the system more robust and maintainable.

## Getting Started

1. Configure MQTT and Redis settings in `config.toml`.
2. Start the IoT Subscriber service.
3. (Optional) Deploy one or more downstream consumer services that read from Redis.

---

**Note:**
- This service does **not** process, transform, or store data beyond pushing it to Redis.
- All downstream processing (e.g., writing to PostgreSQL, preprocessing, analytics) must be implemented in separate modules/services.

For more details, see the code and configuration files in this repository.
