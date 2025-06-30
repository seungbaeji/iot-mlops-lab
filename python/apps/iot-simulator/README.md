# simulator

The **simulator** is a core component of the IoT MLOps Lab project. It acts as a FastAPI-based IoT data simulator, generating and publishing synthetic sensor data to an MQTT broker for downstream processing and MLOps experimentation.

---

## Features

- **FastAPI-based API**: Provides a modern web API for controlling and monitoring the simulator.
- **Sensor Data Generation**: Simulates multiple devices and sensor types with configurable parameters.
- **MQTT Publishing**: Publishes generated sensor data to a specified MQTT broker and topic.
- **Configurable**: All major parameters (device count, publish interval, MQTT, logging, etc.) are configurable via TOML files.
- **Observability**: Integrated metrics (Prometheus), tracing (OpenTelemetry/Tempo), and structured logging.
- **Graceful Shutdown**: Handles signals for safe shutdown and resource cleanup.
- **Testable**: Includes pytest-based test suite and sample configuration.

---

## Directory Structure

```
simulator/
├── config/
│   ├── config.toml         # Main simulator configuration
│   ├── logger.toml         # Logging configuration
│   └── mosquitto.conf/     # (Optional) MQTT broker config
├── src/
│   └── simulator/
│       ├── __init__.py
│       ├── configs.py
│       ├── main.py
│       ├── observability.py
│       ├── router.py
│       ├── simulator.py
│       └── ...
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── mocks.py
│   ├── test_api.py
│   ├── test_config.py
│   └── test_simulator.py
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
- MQTT broker (can be run via Docker Compose)

### 2. Installation

```bash
# install Tools
brew install pipx
pipx install uv

# install dependencies
uv venv --python 3.12
uv python pin 3.12
uv sync
```

### 3. Configuration

Edit `config/config.toml` to set your MQTT broker, device simulation, and publishing parameters.
Edit `config/logger.toml` for logging preferences.

### 4. Running the Service

**Standalone (local):**
```bash
poetry run python -m simulator.main --config config/config.toml --log-config config/logger.toml
```

**With Docker Compose (recommended for full stack):**
```bash
docker compose up --build
```

---

## Configuration Example (`config.toml`)

```toml
[simulator]
device_count = 10
publish_interval = 2

[mqtt]
host = "mqtt"
port = 1883
topic = "sensors/{device_id}"
qos = 0

[observability]
trace_endpoint = "http://otel-collector:4318/v1/traces"
service_name = "simulator"
prometheus_port = 8000
```

---

## Observability

- **Metrics**: Exposed at `/metrics` (Prometheus format, port configurable)
- **Tracing**: OpenTelemetry spans sent to the configured collector (e.g., Tempo)
- **Logging**: Structured JSON logs, configurable via `logger.toml`

---

## Health & Resilience

- Graceful shutdown on SIGTERM/SIGINT
- Robust error handling for MQTT publishing and API endpoints

---

## Testing

```bash
poetry run pytest
```

## Acknowledgements

- [FastAPI](https://fastapi.tiangolo.com/)
- [aiomqtt](https://github.com/sbtinstruments/aiomqtt)
- [OpenTelemetry](https://opentelemetry.io/)
- [Prometheus](https://prometheus.io/)
- [Grafana](https://grafana.com/)
