import logging
import os
import tomllib
from pathlib import Path
from typing import List, Optional

from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class RedisConfig(BaseSettings):
    host: str
    port: int
    stream: str
    group: str
    consumers: Optional[List[str]] = None  # List of worker names
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
    name: str
    batch_size: int = 100
    block_ms: int = 1000
    retry_delay_sec: int = 2
    observability: Optional["ObservabilityConfig"] = None
    model_config = {"env_prefix": "WORKER_", "env_file": ".env"}

    @classmethod
    def _load_workers(cls, raw: dict) -> list["WorkerConfig"]:
        """
        Parse all [worker.worker-x] sections and attach their corresponding
        [worker.worker-x.observability] config if present.
        """
        workers = []
        worker_section = raw.get("worker", {})
        for name, worker_values in worker_section.items():
            # Remove 'observability' if present to avoid duplicate keyword
            worker_values = dict(worker_values)  # copy to avoid mutating original
            obs_section = worker_values.pop("observability", None)
            observability = ObservabilityConfig(**obs_section) if obs_section else None
            worker = cls(**worker_values, observability=observability)
            workers.append(worker)
        return workers

    @staticmethod
    def filter(
        workers: list["WorkerConfig"], args_workers: Optional[list[str]]
    ) -> list["WorkerConfig"]:
        """
        args > env > config
        """
        # 1. args_workers
        if args_workers:
            return [worker for worker in workers if worker.name in args_workers]
        # 2. env_workers
        env_workers = os.environ.get("WORKERS")
        if env_workers:
            names = [w.strip() for w in env_workers.split(",") if w.strip()]
            return [worker for worker in workers if worker.name in names]
        return workers


class ObservabilityConfig(BaseSettings):
    service_name: str
    trace_endpoint: str
    prometheus_port: int
    model_config = {"env_prefix": "OBS_", "env_file": ".env"}


class AppConfig(BaseSettings):
    redis: RedisConfig
    postgres: PostgresConfig
    workers: list[WorkerConfig]
    observability: Optional[ObservabilityConfig] = None

    @staticmethod
    def load(path: str | Path = "config/config.toml") -> "AppConfig":
        path = Path(path).resolve()
        logger.debug(f"Loading config from: {path}")
        if not path.is_file():
            raise FileNotFoundError(f"Config file not found: {path}")

        with path.open("rb") as f:
            raw = tomllib.load(f)

        workers = WorkerConfig._load_workers(raw)

        return AppConfig(
            redis=RedisConfig(**raw["redis"]),
            postgres=PostgresConfig(**raw["postgres"]),
            workers=workers,
            observability=(
                ObservabilityConfig(**raw["observability"])
                if "observability" in raw
                else None
            ),
        )
