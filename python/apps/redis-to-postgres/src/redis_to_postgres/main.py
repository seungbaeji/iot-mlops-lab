import argparse
import asyncio
import logging
import logging.config
import sys
import tomllib
from pathlib import Path

from prometheus_client import start_http_server

from redis_to_postgres.config import AppConfig, WorkerConfig
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
    parser.add_argument(
        "--workers",
        type=str,
        default=None,
        nargs="+",
        help="worker names to run concurrently. ex) --workers worker-1 worker-2",
    )
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

        # 여러 worker 동시 실행
        async def run_all() -> None:
            tracer = (
                get_tracer(config.observability.service_name)
                if config.observability
                else None
            )

            pg_manager = await PostgresManager.create(config.postgres, tracer)

            try:
                tasks: list[asyncio.Task[None]] = []
                for worker_conf in WorkerConfig.filter(config.workers, args.workers):
                    logger.info(f"Starting worker: {worker_conf.name}")
                    redis_manager = await RedisManager.create(
                        config.redis, worker_conf, tracer
                    )
                    worker = RedisStreamToPostgresWorker(
                        pg_manager, redis_manager, worker_conf, tracer
                    )

                    if worker_conf.observability:
                        init_tracing(
                            worker_conf.observability.service_name,
                            worker_conf.observability.trace_endpoint,
                        )
                        start_http_server(worker_conf.observability.prometheus_port)
                        logger.info(
                            f"Prometheus HTTP server started on :{worker_conf.observability.prometheus_port} for {worker_conf.name}"
                        )
                        worker.tracer = get_tracer(
                            worker_conf.observability.service_name
                        )
                        logger.info(f"Tracing initialized for {worker_conf.name}")

                    tasks.append(asyncio.create_task(worker.run()))
                await asyncio.gather(*tasks)
            finally:
                await pg_manager.close()

        asyncio.run(run_all())
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
