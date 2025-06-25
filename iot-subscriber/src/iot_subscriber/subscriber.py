import asyncio
import json
import logging
from typing import List, Optional

import asyncpg
from aiomqtt import Client, MqttCodeError, MqttError
from opentelemetry.trace import Tracer

from iot_subscriber.config import AppConfig
from iot_subscriber.observability import Metrics, get_span_context

logger = logging.getLogger(__name__)


class PostgreSQLConnectionManager:
    """DB 연결 및 커넥션 관리만 담당"""

    def __init__(self, config: AppConfig, tracer: Optional[Tracer] = None):
        self.config = config
        self.tracer = tracer
        self._conn: Optional[asyncpg.Connection] = None
        self._lock = asyncio.Lock()

    async def __aenter__(self) -> asyncpg.Connection:
        await self._ensure_connection()
        return self._conn

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def _ensure_connection(self):
        with get_span_context(self.tracer, "db_connect") as span:
            async with self._lock:
                retry = 0
                while True:
                    if self._conn and not self._conn.is_closed():
                        span.set_attribute("retry", retry)
                        return
                    logger.info("Connecting to PostgreSQL (asyncpg).")
                    try:
                        self._conn = await asyncpg.connect(
                            user=self.config.database.user,
                            password=self.config.database.password,
                            database=self.config.database.name,
                            host=self.config.database.host,
                            port=self.config.database.port,
                        )
                        logger.info("Successfully connected to PostgreSQL.")
                        span.set_attribute("retry", retry)
                        return
                    except Exception as e:
                        logger.error(f"Failed to connect to PostgreSQL: {e}")
                        self._conn = None
                        retry += 1
                        await asyncio.sleep(5)  # 혹은 config에서 재시도 간격 사용

    async def get(self) -> asyncpg.Connection:
        async with self._lock:
            if not self._conn or self._conn.is_closed():
                logger.warning(
                    "PostgreSQL connection lost or not initialized. Attempting to re-establish connection."
                )
                await self._ensure_connection()
            return self._conn

    async def close(self):
        async with self._lock:
            if self._conn and not self._conn.is_closed():
                await self._conn.close()
            self._conn = None
            logger.info("PostgreSQL connection closed.")


class BatchWriter:
    """DB에 batch insert만 담당"""

    def __init__(
        self, conn_manager: PostgreSQLConnectionManager, tracer: Optional[Tracer] = None
    ):
        self.conn_manager = conn_manager
        self.tracer = tracer

    async def write(self, batch: List[dict]):
        if not batch:
            return
        with get_span_context(self.tracer, "db_insert") as span:
            conn = await self.conn_manager.get()
            records = [
                (
                    item["device_id"],
                    item["timestamp"],
                    item["temperature"],
                    item["humidity"],
                )
                for item in batch
            ]
            try:
                await conn.executemany(
                    """
                    INSERT INTO sensor_data (device_id, timestamp, temperature, humidity)
                    VALUES ($1, $2, $3, $4)
                    """,
                    records,
                )
                logger.info(f"Successfully inserted {len(records)} records into DB.")
                span.set_attribute("batch_size", len(batch))
                span.set_attribute("records", len(records))
                Metrics.db_insert_total.inc()
            except Exception as e:
                logger.exception(f"PostgreSQL error during batch insert: {e}")
                Metrics.db_insert_failure_total.inc()
                raise


class SubscriberController:
    """전체 데이터 파이프라인(수신, 버퍼, flush, 장애복구 등) 담당"""

    def __init__(self, config: AppConfig, tracer: Optional[Tracer] = None):
        self.config = config
        self.tracer = tracer
        self.conn_manager = PostgreSQLConnectionManager(config, tracer)
        self.queue = asyncio.Queue(maxsize=1000)
        self.batch_writer = BatchWriter(self.conn_manager, tracer)
        self._immediate_flush_event = asyncio.Event()

    async def handle_message(self, message):
        # aiomqtt의 message는 topic, payload 속성을 가짐
        data = json.loads(message.payload.decode())
        await self.queue.put(data)
        Metrics.buffer_current_size.set(self.queue.qsize())
        # batch_size 도달 시 즉시 flush 트리거
        if self.queue.qsize() >= self.config.subscriber.batch_size:
            self._immediate_flush_event.set()

    async def consume_mqtt_messages(self):
        reconn_delay_sec = self.config.subscriber.mqtt_reconn_delay_sec
        while True:
            try:
                async with Client(
                    self.config.mqtt.host, port=self.config.mqtt.port
                ) as client:
                    await client.subscribe(
                        self.config.mqtt.topic, qos=self.config.mqtt.qos
                    )
                    logger.info(
                        f"Successfully connected to MQTT broker: {self.config.mqtt.host}:{self.config.mqtt.port}"
                    )
                    logger.info(f"Subscribed to topic: {self.config.mqtt.topic}")
                    async for message in client.messages:
                        try:
                            await self.handle_message(message)
                        except Exception as e:
                            logger.error(f"Error handling message: {e}")
            except (MqttError, MqttCodeError) as e:
                logger.warning(f"MQTT connection lost/failed: {e}, {reconn_delay_sec=}")
                await asyncio.sleep(reconn_delay_sec)
            except Exception as e:
                logger.error(f"Unexpected error: {e}, {reconn_delay_sec=}")
                await asyncio.sleep(reconn_delay_sec)

    async def batch_flusher(self):
        batch_size = self.config.subscriber.batch_size
        flush_interval = self.config.subscriber.flush_interval
        while True:
            # flush_interval 또는 즉시 flush 이벤트 중 먼저 발생하는 쪽 대기
            try:
                await asyncio.wait_for(
                    self._immediate_flush_event.wait(), timeout=flush_interval
                )
            except asyncio.TimeoutError:
                pass  # flush_interval 경과

            self._immediate_flush_event.clear()
            batch = []
            while len(batch) < batch_size and not self.queue.empty():
                batch.append(self.queue.get_nowait())
            if batch:
                await self.batch_writer.write(batch)
                Metrics.buffer_current_size.set(self.queue.qsize())

    async def run(self):
        err_retry_delay_sec = self.config.subscriber.error_retry_delay_sec
        async with self.conn_manager:
            while True:
                try:
                    consumer_task = asyncio.create_task(self.consume_mqtt_messages())
                    flusher_task = asyncio.create_task(self.batch_flusher())
                    await asyncio.gather(consumer_task, flusher_task)
                except Exception as e:
                    logger.error(
                        f"Critical error occurred: {e}, {err_retry_delay_sec=}"
                    )
                    await asyncio.sleep(err_retry_delay_sec)

    async def close(self):
        logger.info("Application resources closed.")
