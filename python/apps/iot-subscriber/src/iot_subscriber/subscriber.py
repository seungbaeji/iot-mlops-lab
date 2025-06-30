import asyncio
import json
import logging
from contextlib import suppress
from typing import Any

import redis.asyncio as aioredis
from aiomqtt import Client, MqttCodeError, MqttError
from opentelemetry.trace import Tracer

from iot_subscriber.config import AppConfig
from iot_subscriber.observability import Metrics, get_span_context
from iot_subscriber.queues import AsyncBatchQueueWrapper

logger = logging.getLogger(__name__)


class QueueWriter:
    """Pushes batch data to Redis stream instead of List"""

    def __init__(
        self,
        redis_url: str,
        stream_name: str,
        maxlen: int,
        tracer: Tracer | None = None,
    ):
        self.maxlen = maxlen
        self.redis_url = redis_url
        self.stream_name = stream_name
        self.tracer = tracer
        self.redis: aioredis.Redis | None = None

    def connect(self) -> None:
        if self.redis is None:
            self.redis = aioredis.from_url(self.redis_url)  # type: ignore[no-untyped-call]

    async def write(self, batch: list[dict[str, Any]]) -> None:
        if not batch:
            return
        self.connect()
        assert self.redis is not None

        with get_span_context(self.tracer, "redis_stream_push") as span:
            for item in batch:
                await self.redis.xadd(
                    self.stream_name,
                    {"data": json.dumps(item)},
                    maxlen=self.maxlen,
                    approximate=True,
                )
            logger.info(
                f"Pushed {len(batch)} records to Redis stream '{self.stream_name}'."
            )
            if span:
                span.set_attribute("batch_size", len(batch))
            Metrics.redis_stream_push_total.inc()
            Metrics.redis_stream_records_pushed_total.inc(len(batch))


class SubscriberController:
    """전체 데이터 파이프라인(수신, 버퍼, flush, 장애복구 등) 담당"""

    def __init__(self, config: AppConfig, tracer: Tracer | None = None):
        self.config = config
        self.tracer = tracer

        redis_url = f"redis://{config.redis.host}:{config.redis.port}/0"
        stream_name = config.redis.stream_name

        self.batch_writer = QueueWriter(
            redis_url, stream_name, config.redis.maxlen, tracer
        )
        self.batch_writer.connect()

        self.queue = AsyncBatchQueueWrapper(
            min_batch_size=config.subscriber.min_batch_size,
            max_batch_size=config.subscriber.max_batch_size,
            initial_batch_size=config.subscriber.batch_size,
        )
        self._flush_event = asyncio.Event()

    async def run(self) -> None:
        await asyncio.gather(
            self.mqtt_consumer(),
            self.flush_loop(),
        )

    async def mqtt_consumer(self) -> None:
        reconn_delay_sec = self.config.subscriber.mqtt_reconn_delay_sec
        err_retry_delay_sec = self.config.subscriber.error_retry_delay_sec

        mqtt_host = self.config.mqtt.host
        mqtt_port = self.config.mqtt.port
        mqtt_topic = self.config.mqtt.topic
        mqtt_qos = self.config.mqtt.qos

        while True:
            try:
                async with Client(mqtt_host, port=mqtt_port) as client:
                    await client.subscribe(mqtt_topic, qos=mqtt_qos)
                    logger.info(f"Connected to MQTT broker: {mqtt_host}:{mqtt_port}")
                    logger.info(f"Subscribed to topic: {mqtt_topic}")
                    async for message in client.messages:
                        decoded: str | int | float | bool | None = (
                            message.payload.decode()
                            if isinstance(message.payload, bytes | bytearray)
                            else message.payload
                        )
                        data = (
                            json.loads(decoded) if isinstance(decoded, str) else decoded
                        )
                        await self.queue.put(data)
                        if self.queue.queue.qsize() >= self.queue.batch_size:
                            self._flush_event.set()
            except (MqttError, MqttCodeError) as e:
                logger.warning(f"MQTT connection lost/failed: {e}, {reconn_delay_sec=}")
                await asyncio.sleep(reconn_delay_sec)
            except Exception as e:
                logger.error(f"Critical error occurred: {e}, {err_retry_delay_sec=}")
                await asyncio.sleep(err_retry_delay_sec)

    async def flush_loop(self) -> None:
        flush_interval = self.config.subscriber.flush_interval
        while True:
            try:
                await asyncio.wait_for(self._flush_event.wait(), timeout=flush_interval)
            except TimeoutError:
                suppress(TimeoutError)
            self._flush_event.clear()
            await self.flush_batch()

    async def flush_batch(self) -> None:
        batch = await self.queue.get_batch()
        if batch:
            await self.batch_writer.write([item.get("payload", item) for item in batch])

    async def close(self) -> None:
        batch = await self.queue.get_batch()
        if batch:
            await self.batch_writer.write([item.get("payload", item) for item in batch])
        logger.info("Application resources closed.")
