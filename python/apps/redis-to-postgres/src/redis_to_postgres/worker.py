import asyncio
import json
import logging
from typing import Any

import asyncpg
from opentelemetry.trace import Tracer

from redis_to_postgres.config import WorkerConfig
from redis_to_postgres.database import PostgresManager, RedisManager
from redis_to_postgres.observability import Metrics, get_span_context

logger = logging.getLogger(__name__)


class RedisStreamToPostgresWorker:
    def __init__(
        self,
        pg_manager: PostgresManager,
        redis_manager: RedisManager,
        worker_conf: WorkerConfig,
        tracer: Tracer | None = None,
    ):
        self.pg = pg_manager
        self.redis = redis_manager
        self.worker_conf = worker_conf
        self.tracer = tracer
        self.consumer_retry_delay = worker_conf.retry_delay_sec

    async def run(self) -> None:
        while True:
            try:
                conn = await self.pg.acquire()
                entries = await self.redis.xreadgroup(
                    consumer=self.worker_conf.name,
                    count=self.worker_conf.batch_size,
                    block=self.worker_conf.block_ms,
                )
                if not entries:
                    await self.pg.release(conn)
                    await asyncio.sleep(self.consumer_retry_delay)
                    continue

                # 1. read messages from redis
                for stream, messages in entries:
                    msg_ids = []
                    batch = []

                    # 2. decode messages
                    try:
                        for msg_id, msg_data in messages:
                            batch.append(json.loads(msg_data["data"]))
                            msg_ids.append(msg_id)
                        logger.debug(
                            f"[{self.worker_conf.name}] Successfully decoded {len(batch)} messages"
                        )
                    except Exception as e:
                        logger.error(
                            f"[{self.worker_conf.name}] Error decoding batch: {e}"
                        )
                        continue

                    # 3. write messages to postgres and ack and del from redis
                    try:
                        await self.write_to_postgres(conn, batch)
                        await self.redis.xack(
                            stream, self.redis.redis_conf.group, *msg_ids
                        )
                        Metrics.redis_read_total.inc(len(batch))
                        logger.debug(
                            f"[{self.worker_conf.name}] Successfully wrote {len(batch)} messages to Postgres"
                        )
                    except Exception as e:
                        logger.error(f"Error writing to Postgres: {e}")
                        await asyncio.sleep(self.consumer_retry_delay)
                        continue

                await self.pg.release(conn)
            except Exception as e:
                logger.error(f"Error in worker run loop: {e}")
                await asyncio.sleep(self.consumer_retry_delay)
            break
        return None

    async def write_to_postgres(
        self, conn: asyncpg.Connection, batch: list[dict[str, Any]]
    ) -> None:
        with get_span_context(self.tracer, "db_write_batch") as span:
            try:
                await conn.executemany(
                    """
                    INSERT INTO sensor_data (device_id, timestamp, temperature, humidity)
                    VALUES ($1, $2, $3, $4)
                    """,
                    [
                        (
                            d["device_id"],
                            d["timestamp"],
                            d.get("temperature"),
                            d.get("humidity"),
                        )
                        for d in batch
                    ],
                )
                Metrics.db_insert_total.inc(len(batch))
                if span:
                    span.set_attribute("batch_size", len(batch))
            except Exception as e:
                logger.exception(f"Failed to insert batch to Postgres: {e}")
                Metrics.db_insert_failure_total.inc(len(batch))
                if span:
                    span.set_attribute("error", str(e))
        return None
