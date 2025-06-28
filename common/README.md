# common package

This package provides **shared utilities, observability, and configuration loaders** for reuse across multiple services in the IoT MLOps Lab project.

- **Observability:** Prometheus metrics, OpenTelemetry tracing, JSON/logfmt log formatters, etc.
- **Configuration loader:** TOML-based logging configuration, etc.
- **Other common utilities**

---

## Features

- `MetricFactory`: Easily create and reuse Prometheus Counter, Gauge, Histogram, Summary, and Info metrics per service
- `Tracing`: Provides functions for initializing OpenTelemetry-based tracing, obtaining a tracer instance, and managing span contexts
  - `init_tracing(service_name, trace_endpoint)`: Initializes OpenTelemetry tracing for your service, setting up the tracer provider and exporter. Call this once at application startup to enable distributed tracing.
  - `get_tracer(service_name)`: Returns an OpenTelemetry tracer instance for the given service name. Use this tracer to create and manage spans in your code.
  - `span_context(tracer, name)`: Provides a context manager for creating a named tracing span. Use with the `with` statement to automatically start and end a span for a block of code.
- `JSONFormatter`, `LogfmtFormatter`: Consistent log formatting
- `setup_logger`: Apply TOML-based logging configuration

---

## Installation

### With Poetry

Add the GitHub Packages source to your `pyproject.toml`:
```toml
[[tool.poetry.source]]
name = "github"
url = "https://pypi.pkg.github.com/seungbaeji"
default = false
```

Then install:
```bash
poetry add common --source github
```

### With pip

```bash
pip install --extra-index-url https://pypi.pkg.github.com/seungbaeji common
# If your repo is private, use:
# pip install --extra-index-url https://<USERNAME>:<TOKEN>@pypi.pkg.github.com/seungbaeji common
```

---

## Usage Example

```python
from common.observability import MetricFactory, init_tracing, get_tracer, span_context
from common.config import setup_logger

# Apply logging configuration
setup_logger("config/logger.toml")

# Use metrics
metrics = MetricFactory("my_service")
counter = metrics.counter("requests_total", "Total requests", ["endpoint"])
counter.labels(endpoint="/api").inc()

# Use tracing
init_tracing("my_service", "http://localhost:4318/v1/traces")
tracer = get_tracer("my_service")
with span_context(tracer, "my_span"):
    # ...
    pass
```

---

## Testing

```bash
cd common
poetry run pytest
```

---

## Package Publishing (GitHub Packages)

1. Push a version tag (e.g., v1.0.0) on the main branch
2. The GitHub Actions workflow (`release-common.yaml`) will automatically build, test, and publish the package
3. Other services can install the package via GitHub Packages
