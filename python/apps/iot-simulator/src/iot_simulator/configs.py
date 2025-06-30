import logging
import tomllib
from pathlib import Path

from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class SimulationConfig(BaseSettings):
    frequency_sec: int
    max_devices: int

    model_config = {"env_prefix": "SIMULATION_", "env_file": ".env"}


class MQTTConfig(BaseSettings):
    host: str
    port: int
    topic: str
    qos: int

    model_config = {"env_prefix": "MQTT_", "env_file": ".env"}


class ObservabilityConfig(BaseSettings):
    service_name: str
    trace_endpoint: str
    prometheus_port: int

    model_config = {"env_prefix": "OBSERVABILITY_", "env_file": ".env"}


class ServerConfig(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000

    model_config = {"env_prefix": "SERVER_", "env_file": ".env"}


class AppConfig(BaseSettings):
    simulation: SimulationConfig
    mqtt: MQTTConfig | None = None
    observability: ObservabilityConfig | None = None
    server: ServerConfig | None = None

    @staticmethod
    def load(path: str | Path = "config/config.toml") -> "AppConfig":
        path = Path(path).resolve()
        logger.debug(f"{path=}")
        if not path.is_file():
            raise FileNotFoundError(f"Config file not found: {path}")

        with path.open("rb") as f:
            raw = tomllib.load(f)

        return AppConfig(
            simulation=SimulationConfig(**raw["simulation"]),
            mqtt=MQTTConfig(**raw.get("mqtt", {})) if "mqtt" in raw else None,
            observability=(
                ObservabilityConfig(**raw.get("observability", {}))
                if "observability" in raw
                else None
            ),
            server=ServerConfig(**raw.get("server", {})) if "server" in raw else None,
        )
