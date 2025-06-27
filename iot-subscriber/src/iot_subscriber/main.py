import argparse
import asyncio
import logging
import logging.config
import tomllib
from pathlib import Path

from iot_subscriber.config import AppConfig
from iot_subscriber.observability import get_tracer, init_tracing
from iot_subscriber.subscriber import SubscriberController
from prometheus_client import start_http_server

logger = logging.getLogger(__name__)


def setup_logger(config_path: str) -> None:
    with open(config_path, "rb") as f:
        logging_config = tomllib.load(f)

    file_handler = logging_config.get("handlers", {}).get("file")
    try:
        log_file = file_handler.get("filename") if file_handler else None
        log_path = Path(log_file) if log_file else None
        if log_path:
            log_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(f"Failed to create log directory {log_path.parent}: {e}")

    logging.config.dictConfig(logging_config)
    logger.info("Logger configuration is applied.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default="configs/config.toml")
    parser.add_argument("--log-config", type=str, default="configs/logger.toml")
    args = parser.parse_args()

    config = AppConfig.load(args.config)
    setup_logger(args.log_config)

    tracer = None
    controller = None
    try:
        # Observability init
        if config.observability:
            init_tracing(
                config.observability.service_name, config.observability.trace_endpoint
            )
            tracer = get_tracer(config.observability.service_name)
            start_http_server(config.observability.prometheus_port)
            logger.info(
                f"Prometheus HTTP server started on :{config.observability.prometheus_port}"
            )

        controller = SubscriberController(config, tracer)
        asyncio.run(controller.run())
    finally:
        if controller:
            asyncio.run(controller.close())
        logger.info("iot-subscriber terminated gracefully.")


if __name__ == "__main__":
    main()
