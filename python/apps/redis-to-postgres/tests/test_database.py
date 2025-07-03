import pytest
from unittest.mock import AsyncMock, MagicMock

from redis_to_postgres.database import PostgresManager, RedisManager
from redis_to_postgres.config import PostgresConfig, RedisConfig, WorkerConfig


@pytest.mark.asyncio
async def test_postgres_manager_acquire_release():
    pool = MagicMock()
    pool.acquire = AsyncMock(return_value="conn")
    pool.release = AsyncMock()
    config = PostgresConfig(
        host="localhost", port=5432, database="db", user="user", password="pw"
    )
    manager = PostgresManager(config, pool)
    conn = await manager.acquire()
    assert conn == "conn"
    await manager.release(conn)
    pool.acquire.assert_called_once()
    pool.release.assert_called_once_with("conn")


@pytest.mark.asyncio
async def test_redis_manager_xreadgroup_xack_close():
    redis_client = MagicMock()
    redis_client.xreadgroup = AsyncMock(
        return_value=[("stream", [("id", {"data": "msg"})])]
    )
    redis_client.xack = AsyncMock(return_value=1)
    redis_client.close = AsyncMock()
    redis_conf = RedisConfig(host="localhost", port=6379, stream="s", group="g")
    worker_conf = WorkerConfig(name="worker-1")
    manager = RedisManager(redis_conf, worker_conf, redis_client=redis_client)
    result = await manager.xreadgroup("worker-1", 1, 1000)
    assert result[0][0] == "stream"
    ack_result = await manager.xack("s", "g", "id")
    assert ack_result == 1
    await manager.close()
    redis_client.close.assert_called_once()
