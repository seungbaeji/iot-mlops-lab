import tomllib
from redis_to_postgres.config import (
    AppConfig,
    ObservabilityConfig,
    RedisConfig,
    PostgresConfig,
    WorkerConfig,
)

CONFIG_TEXT = b"""
[redis]
consumer  = "default"
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

[worker]
batch_size      = 3000
block_ms        = 1000
retry_delay_sec = 2
"""


def parse_config_from_text(config_text: bytes) -> AppConfig:
    raw = tomllib.loads(config_text.decode())
    return AppConfig(
        redis=RedisConfig(**raw["redis"]),
        postgres=PostgresConfig(**raw["postgres"]),
        worker=WorkerConfig(**raw["worker"]),
        observability=(
            ObservabilityConfig(**raw["observability"])
            if "observability" in raw
            else None
        ),
    )


def test_app_config_load_from_text():
    config = parse_config_from_text(CONFIG_TEXT)
    assert config.redis.host == "localhost"
    assert config.postgres.user == "lab_admin"
    assert config.observability.service_name == "redis-to-postgres"
    assert config.worker.batch_size == 3000
    assert config.worker.block_ms == 1000
    assert config.worker.retry_delay_sec == 2
