import argparse
import asyncio
import logging
import logging.config
import sys
import tomllib
from pathlib import Path

from prometheus_client import start_http_server

from redis_to_postgres.config import AppConfig
from redis_to_postgres.database import PostgresManager, RedisManager
from redis_to_postgres.observability import get_tracer, init_tracing
from redis_to_postgres.worker import RedisStreamToPostgresWorker

logger = logging.getLogger(__name__)


def setup_logger(config_path: str) -> None:
    with open(config_path, "rb") as f:
        logging_config = tomllib.load(f)

    file_handler = logging_config.get("handlers", {}).get("file")
    try:
        log_file = file_handler.get("filename", "./tmp/redis-to-postgres.log")
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(f"Failed to create log directory {log_path.parent}: {e}")

    logging.config.dictConfig(logging_config)
    logger.info("Logger configuration is applied.")


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default="config/config.toml")
    parser.add_argument("--log-config", type=str, default="config/logger.toml")
    return parser.parse_args()


def main() -> None:
    args = get_args()
    setup_logger(args.log_config)

    logger.debug(f"Starting with args: {args}")
    try:
        config = AppConfig.load(args.config)
        if config.observability:
            init_tracing(
                config.observability.service_name, config.observability.trace_endpoint
            )
            start_http_server(config.observability.prometheus_port)
            logger.info(
                f"Prometheus HTTP server started on :{config.observability.prometheus_port}"
            )

        tracer = get_tracer(config.observability.service_name)
        logger.info(f"Starting worker")

        async def run_worker() -> None:
            try:
                pg_manager = await PostgresManager.create(config.postgres, tracer)
                redis_manager = await RedisManager.create(config.redis, tracer)
                worker = RedisStreamToPostgresWorker(
                    pg_manager, redis_manager, config.worker, tracer
                )
                await worker.run()
            finally:
                await pg_manager.close()
                await redis_manager.close()

        asyncio.run(run_worker())
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Received interrupt signal. Shutting down gracefully...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("redis-to-postgres terminated gracefully.")


if __name__ == "__main__":
    main()
