import pytest
import tomllib
from redis_to_postgres.config import AppConfig, WorkerConfig, ObservabilityConfig
from pathlib import Path

CONFIG_TEXT = b'''
[redis]
consumers = ["worker-1", "worker-2"]
group     = "sensor_group"
host      = "localhost"
port      = 6379
stream    = "sensor_data_stream"
ttl       = 3600

[postgres]
database        = "iot_ml_lab"
host            = "localhost"
max_retries     = 3
password        = "changeme"
pool_max_size   = 5
pool_min_size   = 1
port            = 5432
retry_delay_sec = 1
user            = "lab_admin"

[observability]
prometheus_port = 8011
service_name    = "redis-to-postgres"
trace_endpoint  = "http://localhost:4318/v1/traces"

[worker.worker-1]
batch_size      = 100
block_ms        = 1000
name            = "worker-1"
retry_delay_sec = 2

[worker.worker-2]
batch_size      = 100
block_ms        = 1000
name            = "worker-2"
retry_delay_sec = 2

[worker.worker-1.observability]
prometheus_port = 8012
service_name    = "redis-to-postgres-worker-1"
trace_endpoint  = "http://localhost:4318/v1/traces"

[worker.worker-2.observability]
prometheus_port = 8013
service_name    = "redis-to-postgres-worker-2"
trace_endpoint  = "http://localhost:4318/v1/traces"
'''

def parse_config_from_text(config_text: bytes) -> AppConfig:
    raw = tomllib.loads(config_text.decode())
    workers = WorkerConfig._load_workers(raw)
    return AppConfig(
        redis=AppConfig.model_fields['redis'].annotation(**raw["redis"]),
        postgres=AppConfig.model_fields['postgres'].annotation(**raw["postgres"]),
        workers=workers,
        observability=(
            ObservabilityConfig(**raw["observability"]) if "observability" in raw else None
        ),
    )

def test_app_config_load_from_text():
    config = parse_config_from_text(CONFIG_TEXT)
    assert config.redis.host == "localhost"
    assert config.postgres.user == "lab_admin"
    assert config.observability.service_name == "redis-to-postgres"
    assert len(config.workers) == 2
    names = {w.name for w in config.workers}
    assert "worker-1" in names and "worker-2" in names
    # Check observability for each worker
    for w in config.workers:
        assert w.observability is not None
        assert w.observability.service_name.startswith("redis-to-postgres-worker-")

def test_worker_filter_args_from_text():
    config = parse_config_from_text(CONFIG_TEXT)
    filtered = WorkerConfig.filter(config.workers, ["worker-2"])
    assert len(filtered) == 1
    assert filtered[0].name == "worker-2"

def test_worker_filter_env_from_text(monkeypatch):
    config = parse_config_from_text(CONFIG_TEXT)
    monkeypatch.setenv("WORKERS", "worker-1")
    filtered = WorkerConfig.filter(config.workers, None)
    assert len(filtered) == 1
    assert filtered[0].name == "worker-1"
