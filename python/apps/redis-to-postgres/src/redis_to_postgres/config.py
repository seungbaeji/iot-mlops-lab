import logging
import tomllib
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class RedisConfig(BaseSettings):
    consumer: str
    host: str
    port: int
    stream: str
    group: str
    ttl: int = 3600
    model_config = {"env_prefix": "REDIS_", "env_file": ".env"}


class PostgresConfig(BaseSettings):
    host: str
    port: int
    database: str
    user: str
    password: str
    pool_min_size: int = 1  # asyncpg pool min size
    pool_max_size: int = 5  # asyncpg pool max size
    max_retries: int = 5  # Number of retries for DB connection
    retry_delay_sec: float = 3.0  # Delay between retries in seconds
    model_config = {"env_prefix": "PG_", "env_file": ".env"}


class WorkerConfig(BaseSettings):
    batch_size: int = 100
    block_ms: int = 1000
    retry_delay_sec: int = 2
    model_config = {"env_prefix": "WORKER_", "env_file": ".env"}


class ObservabilityConfig(BaseSettings):
    service_name: str
    trace_endpoint: str
    prometheus_port: int
    model_config = {"env_prefix": "OBS_", "env_file": ".env"}


class AppConfig(BaseSettings):
    redis: RedisConfig
    postgres: PostgresConfig
    worker: WorkerConfig
    observability: Optional[ObservabilityConfig] = None

    @staticmethod
    def load(path: str | Path = "config/config.toml") -> "AppConfig":
        path = Path(path).resolve()
        logger.debug(f"Loading config from: {path}")
        if not path.is_file():
            raise FileNotFoundError(f"Config file not found: {path}")

        with path.open("rb") as f:
            raw = tomllib.load(f)

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
