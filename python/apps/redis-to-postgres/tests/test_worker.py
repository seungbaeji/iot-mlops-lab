import pytest
from unittest.mock import AsyncMock, MagicMock

from redis_to_postgres.worker import RedisStreamToPostgresWorker
from redis_to_postgres.config import WorkerConfig
from redis_to_postgres.database import PostgresManager, RedisManager


@pytest.fixture
def worker_config():
    return WorkerConfig(
        batch_size=2,
        block_ms=1000,
        retry_delay_sec=1,
    )


@pytest.mark.asyncio
async def test_worker_run_handles_decoding_error(worker_config):
    pg_manager = MagicMock(spec=PostgresManager)
    pg_manager.acquire = AsyncMock(return_value="conn")
    pg_manager.release = AsyncMock()
    redis_manager = MagicMock(spec=RedisManager)
    # Simulate a message with invalid JSON
    redis_manager.xreadgroup = AsyncMock(
        return_value=[("stream", [("id1", {"data": "not-json"})])]
    )
    worker = RedisStreamToPostgresWorker(pg_manager, redis_manager, worker_config)
    # Should not raise, should skip batch on decode error
    await worker.run()
    pg_manager.acquire.assert_called_once()
    pg_manager.release.assert_called_once_with("conn")
    redis_manager.xreadgroup.assert_called_once()


@pytest.mark.asyncio
async def test_worker_run_handles_postgres_error(worker_config):
    pg_manager = MagicMock(spec=PostgresManager)
    pg_manager.acquire = AsyncMock(return_value="conn")
    pg_manager.release = AsyncMock()
    redis_manager = MagicMock(spec=RedisManager)
    # Simulate a valid message
    redis_manager.xreadgroup = AsyncMock(
        return_value=[
            (
                "stream",
                [
                    (
                        "id1",
                        {
                            "data": '{"device_id": "dev1", "timestamp": 1, "temperature": 22.5, "humidity": 55.0}'
                        },
                    )
                ],
            )
        ]
    )
    # Patch write_to_postgres to raise
    worker = RedisStreamToPostgresWorker(pg_manager, redis_manager, worker_config)
    worker.write_to_postgres = AsyncMock(side_effect=Exception("DB error"))
    # Should not raise, should handle error
    await worker.run()
    pg_manager.acquire.assert_called_once()
    pg_manager.release.assert_called_once_with("conn")
    redis_manager.xreadgroup.assert_called_once()


@pytest.mark.asyncio
async def test_write_to_postgres_handles_insert_failure(worker_config):
    pg_manager = MagicMock(spec=PostgresManager)
    conn = MagicMock()
    batch = [
        {"device_id": "dev1", "timestamp": 1, "temperature": 22.5, "humidity": 55.0},
    ]
    worker = RedisStreamToPostgresWorker(pg_manager, MagicMock(), worker_config)
    # Patch conn.executemany to raise
    conn.executemany = AsyncMock(side_effect=Exception("Insert failed"))
    # Should not raise, should handle error internally
    await worker.write_to_postgres(conn, batch)
    conn.executemany.assert_called_once()


@pytest.mark.asyncio
async def test_worker_run_successful_flow(worker_config):
    pg_manager = MagicMock(spec=PostgresManager)
    conn = MagicMock()
    pg_manager.acquire = AsyncMock(return_value=conn)
    pg_manager.release = AsyncMock()
    redis_manager = MagicMock(spec=RedisManager)
    # Set up redis_conf.group for the mock
    redis_manager.redis_conf = MagicMock()
    redis_manager.redis_conf.group = "sensor_group"
    # Simulate a valid message
    redis_manager.xreadgroup = AsyncMock(
        return_value=[
            (
                "stream",
                [
                    (
                        "id1",
                        {
                            "data": '{"device_id": "dev1", "timestamp": 1, "temperature": 22.5, "humidity": 55.0}'
                        },
                    )
                ],
            )
        ]
    )
    redis_manager.xack = AsyncMock()
    # Patch conn.executemany to succeed
    conn.executemany = AsyncMock()
    worker = RedisStreamToPostgresWorker(pg_manager, redis_manager, worker_config)
    await worker.run()
    pg_manager.acquire.assert_called_once()
    pg_manager.release.assert_called_once_with(conn)
    redis_manager.xreadgroup.assert_called_once()
    redis_manager.xack.assert_called_once()
