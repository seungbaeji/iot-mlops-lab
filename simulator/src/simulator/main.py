import argparse
import logging
import logging.config
import tomllib
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import paho.mqtt.client as mqtt
from fastapi import FastAPI
from prometheus_client import make_wsgi_app, start_http_server
from starlette.middleware.wsgi import WSGIMiddleware

from simulator.configs import AppConfig
from simulator.observability import JSONFormatter, get_tracer, init_tracing
from simulator.router import create_router
from simulator.simulator import SimulatorController, default_payload

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

app: FastAPI = FastAPI()
app.mount("/metrics", WSGIMiddleware(make_wsgi_app()))


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="IoT 시뮬레이터 실행")
    parser.add_argument("--config", type=Path, default=Path("config/config.toml"))
    parser.add_argument("--log-config", type=Path, default=Path("config/logging.toml"))
    return parser.parse_args()


def patch_uvicorn_loggers() -> None:
    formatter = JSONFormatter()
    for name in ["uvicorn", "uvicorn.error", "uvicorn.access"]:
        logger = logging.getLogger(name)
        for handler in logger.handlers:
            handler.setFormatter(formatter)


def init_logging(config_path: Path) -> None:
    with open(config_path, "rb") as f:
        logging_config = tomllib.load(f)

    file_handler = logging_config.get("handlers", {}).get("file")
    try:
        log_file = file_handler.get("filename") if file_handler else None
        log_path = Path(log_file) if log_file else None
        log_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.warning(f"Failed to create log directory {log_path.parent}: {e}")

    logging.config.dictConfig(logging_config)
    patch_uvicorn_loggers()
    logger.info("Logger Congiuration is applied")


def init_app(
    app: FastAPI,
    config: AppConfig,
    mqtt_client: Optional[mqtt.Client] = None,
) -> None:
    """전역 FastAPI 앱에 구성 주입 및 lifespan 설정."""
    app.state.config = config

    simulator = SimulatorController(
        config=config,
        payload_generator=default_payload,
    )
    app.state.simulator = simulator
    app.include_router(create_router(simulator))

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        logger.info("lifespan 시작: Observability, MQTT 초기화")

        # Observability
        if config.observability:
            init_tracing(
                service_name=config.observability.service_name,
                trace_endpoint=config.observability.trace_endpoint,
            )
            start_http_server(config.observability.prometheus_port)
            logger.info("Prometheus 메트릭 서버 시작")

            tracer = get_tracer()
            app.state.simulator.set_tracer(tracer)

        # MQTT
        client = mqtt_client or mqtt.Client(protocol=mqtt.MQTTv311)
        if mqtt_client is None and config.mqtt:
            client.connect(config.mqtt.host, config.mqtt.port)
            client.loop_start()
        app.state.simulator.set_mqtt_client(client)

        logger.info("lifespan 초기화 완료")
        yield
        logger.info("애플리케이션 종료 처리")
        await simulator.stop_all()

    app.router.lifespan_context = lifespan


def main() -> None:
    import uvicorn

    args = get_args()
    logger.debug(f"{args.log_config=}")
    logger.debug(f"{args.config=}")

    init_logging(args.log_config)
    config = AppConfig.load(args.config)
    logger.info("Configuration is Done")

    # 앱 구성 주입
    init_app(app, config)
    logger.info("Initialized Application")

    try:
        # 애플리케이션 실행
        uvicorn.run(
            "simulator.main:app",
            host=config.server.host if config.server else "0.0.0.0",
            port=config.server.port if config.server else 8000,
            log_level="info",
        )
    except Exception as e:
        logger.exception(e)


if __name__ == "__main__":
    main()
