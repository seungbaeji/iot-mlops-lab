# IoT MLOps Lab

This is an MLOps project for practicing the collection, processing, inference, observability, and deployment of data generated in IoT environments.

## Components

- **simulator/** : IoT data simulator
- **iot-subscriber/** : IoT data ingestion and processing
- **inference-client/** : Model inference request client
- **tritron-server/** : Model serving server (planned)
- **model/** : Machine learning models and training code
- **observability/** : Observability setup (monitoring, tracing, logging, profiling, etc.)
- **data-pipeline/** : Data pipeline configuration (planned)
- **compose.yaml** : Docker Compose orchestration for all services

## Getting Started

1. Install Docker and Docker Compose
2. Run all services with the following command:

```bash
docker compose up --build
```

## Purpose

- Practice end-to-end IoT data MLOps pipeline
- Experience automation from data generation → ingestion → inference → observability (monitoring, tracing, logging, profiling, etc.) → deployment

## Service Endpoints

After running docker compose, you can access various observability and management UIs at the following sites:

- **Grafana (Observability dashboard: monitoring, tracing, etc.):** [http://localhost:3000](http://localhost:3000)
    - Default account: admin / admin
- **Prometheus (Metrics collection):** [http://localhost:9090](http://localhost:9090)
- **Simulator (FastAPI-based sensor simulator):** [http://localhost:8000/docs](http://localhost:8000/docs)
    - Test and explore APIs via FastAPI Swagger UI
- **Other services**
    - Additional web UIs may be available for services like inference-client, depending on your setup.

> Note: Service ports may differ if you change them in compose.yaml. Please check the actual port and URL if needed.
