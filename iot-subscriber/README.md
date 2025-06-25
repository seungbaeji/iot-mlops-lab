# iot-subscriber

The **iot-subscriber** is a core component of the IoT MLOps Lab project. It is responsible for ingesting sensor data from an MQTT broker, buffering and batching the data, and reliably storing it in a PostgreSQL database. The service is designed for production-grade observability, resilience, and extensibility.

---

## Features

- **MQTT Ingestion**: Subscribes to one or more MQTT topics and receives real-time sensor data.
- **Batch Buffering**: Buffers incoming messages and writes them to the database in configurable batches for efficiency.
- **Asynchronous Processing**: Fully async implementation using `asyncio` and `asyncpg` for high throughput.
- **Resilient Connections**: Automatic reconnection logic for both MQTT and PostgreSQL.
- **Observability**: Integrated metrics (Prometheus), tracing (OpenTelemetry/Tempo), and structured logging.
- **Configurable**: All major parameters (MQTT, DB, batching, logging, etc.) are configurable via TOML files.
- **Graceful Shutdown**: Handles signals for safe shutdown and resource cleanup.
- **Testable**: Includes pytest-based test suite and sample configuration.

---

## Directory Structure

```
iot-subscriber/
├── config/
│   ├── config.toml         # Main service configuration
│   └── logger.toml         # Logging configuration
├── src/
│   └── iot_subscriber/
│       ├── __init__.py
│       ├── config.py
│       ├── main.py
│       ├── observability.py
│       ├── subscriber.py
│       └── ...
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_config.py
│   └── test_subscriber.py
├── Dockerfile
├── pyproject.toml
├── README.md
└── ...
```

---

## Getting Started

### 1. Prerequisites

- Python 3.12+
- Docker & Docker Compose (for full stack integration)
- PostgreSQL and MQTT broker (can be run via Docker Compose)

### 2. Installation

```bash
# Clone the repository (if not already)
git clone <your-repo-url>
cd iot-subscriber

# Install dependencies
poetry install
```

### 3. Configuration

Edit `config/config.toml` to set your MQTT broker, PostgreSQL, and batching parameters.  
Edit `config/logger.toml` for logging preferences.

### 4. Running the Service

**Standalone (local):**
```bash
poetry run python -m iot_subscriber.main --config config/config.toml --log-config config/logger.toml
```

**With Docker Compose (recommended for full stack):**
```bash
docker compose up --build
```

---

## Configuration Example (`config.toml`)

```toml
[mqtt]
host = "mqtt"
port = 1883
topic = "sensors/#"
qos = 0

[database]
name = "iot_ml_lab"
user = "lab_admin"
password = "changeme"
host = "postgresql"
port = 5432

[subscriber]
batch_size = 20
flush_interval = 5
mqtt_reconn_delay_sec = 5
error_retry_delay_sec = 5

[observability]
trace_endpoint = "http://otel-collector:4318/v1/traces"
service_name = "iot-subscriber"
prometheus_port = 8001
```

---

## Observability

- **Metrics**: Exposed at `/metrics` (Prometheus format, port configurable)
- **Tracing**: OpenTelemetry spans sent to the configured collector (e.g., Tempo)
- **Logging**: Structured JSON logs, configurable via `logger.toml`

---

## Health & Resilience

- Automatic reconnection to MQTT and PostgreSQL on failure
- Graceful shutdown on SIGTERM/SIGINT
- Batch buffer with both time-based and size-based flush

---

## Testing

```bash
poetry run pytest
```

---

## Contributing

Contributions are welcome! Please open issues or pull requests for bug fixes, features, or improvements.

---

## License

This project is licensed under the MIT License.

---

## Authors

- [Your Name or Team]  
- [Project Repository Link]

---

## Acknowledgements

- [asyncpg](https://github.com/MagicStack/asyncpg)
- [aiomqtt](https://github.com/sbtinstruments/aiomqtt)
- [OpenTelemetry](https://opentelemetry.io/)
- [Prometheus](https://prometheus.io/)
- [Grafana](https://grafana.com/)
