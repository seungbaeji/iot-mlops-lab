import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import asyncpg
import redis.asyncio as aioredis
from opentelemetry.trace import Tracer

from redis_to_postgres.config import PostgresConfig, RedisConfig, WorkerConfig
from redis_to_postgres.observability import Metrics, get_span_context

logger = logging.getLogger(__name__)


class PostgresManager:
    def __init__(
        self,
        config: PostgresConfig,
        pool: asyncpg.Pool,
        tracer: Tracer | None = None,
    ):
        self.config = config
        self.tracer = tracer
        self._pool = pool

    @classmethod
    async def create(
        cls,
        config: PostgresConfig,
        tracer: Tracer | None = None,
        max_retries: int | None = None,
        retry_delay: float | None = None,
    ) -> "PostgresManager":
        """
        Create a PostgresManager with retry logic on connection failure.
        max_retries: number of retries before giving up (0 for infinite)
        retry_delay: seconds to wait between retries
        """
        attempt = 0
        with get_span_context(tracer, "create_postgres_pool") as span:
            max_retries = getattr(config, "max_retries", 5)
            retry_delay = getattr(config, "retry_delay_sec", 3.0)
            while True:
                try:
                    pool = await asyncpg.create_pool(
                        user=config.user,
                        password=config.password,
                        database=config.database,
                        host=config.host,
                        port=config.port,
                        min_size=config.pool_min_size,
                        max_size=config.pool_max_size,
                    )
                    span.set_attribute("attempt", attempt)
                    return cls(config, pool, tracer)
                except Exception as e:
                    attempt += 1
                    logger.error(
                        f"Failed to create Postgres pool (attempt {attempt}): {e}"
                    )
                    span.set_attribute("attempt", attempt)
                    span.set_attribute("error", str(e))
                    if max_retries and attempt >= max_retries:
                        logger.error(
                            f"Giving up after {attempt} attempts to connect to Postgres."
                        )
                        span.set_attribute("max_retries", max_retries)
                        span.set_attribute("attempt", attempt)
                        span.set_attribute("error", str(e))
                        raise
                    await asyncio.sleep(retry_delay)

    async def acquire(self) -> asyncpg.Connection:
        """Acquire a connection from the pool."""
        return await self._pool.acquire()

    async def release(self, conn: asyncpg.Connection) -> None:
        """Release a connection back to the pool."""
        await self._pool.release(conn)

    @asynccontextmanager
    async def connection(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """Async context manager for a pooled connection."""
        conn = await self.acquire()
        Metrics.db_connection_pool_size.set(self._pool.size)
        try:
            yield conn
        finally:
            await self.release(conn)

    async def close(self) -> None:
        await self._pool.close()
        logger.info("PostgreSQL pool closed.")


class RedisManager:
    def __init__(
        self,
        redis_conf: RedisConfig,
        tracer: Tracer | None = None,
        redis_client: aioredis.Redis | None = None,
    ):
        self.redis_conf = redis_conf
        self.tracer = tracer
        self.redis: aioredis.Redis | None = redis_client

    @classmethod
    async def create(
        cls,
        redis_conf: RedisConfig,
        tracer: Tracer | None = None,
        redis_client: aioredis.Redis | None = None,
    ) -> "RedisManager":
        if redis_client is None:
            redis_client = aioredis.from_url(  # type: ignore[no-untyped-call]
                f"redis://{redis_conf.host}:{redis_conf.port}",
                encoding="utf-8",
                decode_responses=True,
            )
        # Create stream group if not exists
        try:
            await redis_client.xgroup_create(
                redis_conf.stream,
                redis_conf.group,
                id="0",
                mkstream=True,
            )
        except Exception as e:
            if "BUSYGROUP" in str(e):
                logger.info("Redis stream group already exists.")
            else:
                logger.error(f"Error creating Redis stream group: {e}")
        return cls(redis_conf, tracer, redis_client)

    async def xreadgroup(self, count: int, block: int, **kwargs: Any) -> Any:
        assert self.redis is not None
        return await self.redis.xreadgroup(
            groupname=self.redis_conf.group,
            consumername=self.redis_conf.consumer,
            streams={self.redis_conf.stream: ">"},
            count=count,
            block=block,
            **kwargs,
        )

    async def xack(self, stream: str, group: str, *message_ids: str) -> Any:
        assert self.redis is not None
        return await self.redis.xack(stream, group, *message_ids)

    async def close(self) -> None:
        if self.redis:
            await self.redis.close()
            self.redis = None
            logger.info("Redis connection closed.")
