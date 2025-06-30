import logging
import tomllib
from pathlib import Path

from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class MQTTConfig(BaseSettings):
    host: str
    port: int
    topic: str
    qos: int = 0

    model_config = {"env_prefix": "MQTT_", "env_file": ".env"}


class RedisConfig(BaseSettings):
    host: str
    port: int
    stream_name: str
    maxlen: int = 100000
    model_config = {"env_prefix": "REDIS_", "env_file": ".env"}


class SubscriberConfig(BaseSettings):
    batch_size: int = 100
    min_batch_size: int = 50
    max_batch_size: int = 10000
    flush_interval: int = 5
    mqtt_reconn_delay_sec: int = 5
    error_retry_delay_sec: int = 5
    queue_maxsize: int = 10000

    model_config = {"env_prefix": "SUB_", "env_file": ".env"}


class ObservabilityConfig(BaseSettings):
    service_name: str
    trace_endpoint: str
    prometheus_port: int

    model_config = {"env_prefix": "OBS_", "env_file": ".env"}


class AppConfig(BaseSettings):
    mqtt: MQTTConfig
    redis: RedisConfig
    subscriber: SubscriberConfig
    observability: ObservabilityConfig | None = None

    @staticmethod
    def load(path: str | Path = "configs/config.toml") -> "AppConfig":
        path = Path(path).resolve()
        logger.debug(f"Loading config from: {path}")
        if not path.is_file():
            raise FileNotFoundError(f"Config file not found: {path}")

        with path.open("rb") as f:
            raw = tomllib.load(f)

        return AppConfig(
            mqtt=MQTTConfig(**raw["mqtt"]),
            redis=RedisConfig(**raw["redis"]),
            subscriber=SubscriberConfig(**raw["subscriber"]),
            observability=(
                ObservabilityConfig(**raw["observability"])
                if "observability" in raw
                else None
            ),
        )
