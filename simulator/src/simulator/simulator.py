import asyncio
import json
import logging
import random
import time
from typing import Callable, Optional

import paho.mqtt.client as mqtt
from opentelemetry.trace import Tracer

from simulator.configs import AppConfig, MQTTConfig, SimulationConfig
from simulator.observability import Metrics, get_span_context, get_tracer

logger = logging.getLogger(__name__)


def default_payload(device_id: str) -> dict:
    return {
        "device_id": device_id,
        "timestamp": time.time(),
        "temperature": round(random.uniform(20.0, 35.0), 2),
        "humidity": round(random.uniform(30.0, 70.0), 2),
    }


class PayloadPublisher:
    def __init__(
        self,
        mqtt_config: MQTTConfig,
        mqtt_client: Optional[mqtt.Client] = None,
    ):
        self._mqtt_config = mqtt_config
        self._mqtt_client = mqtt_client

    def set_client(self, client: mqtt.Client) -> None:
        self._mqtt_client = client

    def publish(self, device_id: str, payload: dict) -> None:
        if not self._mqtt_client:
            logger.warning(f"[{device_id}] No MQTT Client. Payload not published.")
            logger.debug(f"[{device_id}] Payload: {json.dumps(payload)}")
            return

        try:
            self._mqtt_client.publish(
                self._mqtt_config.topic,
                json.dumps(payload),
                qos=self._mqtt_config.qos,
            )
            Metrics.mqtt_sent_total.labels(device_id=device_id).inc()
            logger.debug(f"[{device_id}] Published payload.")
        except Exception as e:
            logger.warning(f"[{device_id}] Failed to publish: {e}")

    @property
    def topic(self):
        return self._mqtt_config.topic

    @property
    def host(self):
        return self._mqtt_config.host


class DeviceManager:
    def __init__(self, max_devices: int, frequency_sec: float):
        self._max_devices = max_devices
        self._frequency_sec = frequency_sec
        self._running_tasks: dict[str, asyncio.Task] = {}

    def generate_device_id(self, index: int) -> str:
        return f"device_{index:03d}"

    def start_task(self, device_id: str, task: asyncio.Task) -> None:
        self._running_tasks[device_id] = task
        Metrics.running_devices.set(len(self._running_tasks))
        logger.debug(f"Task started: {device_id}")

    async def stop_task(self, device_id: str) -> None:
        task = self._running_tasks.pop(device_id, None)
        if task:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            logger.info(f"[{device_id}] Task stopped.")
        Metrics.running_devices.set(len(self._running_tasks))

    async def stop_all(self) -> None:
        tasks = list(self._running_tasks.values())
        self._running_tasks.clear()
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        Metrics.running_devices.set(0)

    def current_count(self) -> int:
        return len(self._running_tasks)

    def running_ids(self) -> list[str]:
        return sorted(self._running_tasks.keys())

    def is_device_running(self, device_id: str) -> bool:
        return device_id in self._running_tasks

    @property
    def running(self) -> bool:
        return bool(self._running_tasks)

    @property
    def max_devices(self) -> int:
        return self._max_devices

    @property
    def frequency_sec(self) -> float:
        return self._frequency_sec


class SimulatorController:
    def __init__(
        self,
        config: AppConfig,
        payload_generator: Callable[[str], dict] = default_payload,
    ):
        self._payload_generator = payload_generator
        self._tracer: Optional[Tracer] = None
        self._device_manager = DeviceManager(
            max_devices=config.simulation.max_devices,
            frequency_sec=config.simulation.frequency_sec,
        )
        self._publisher = PayloadPublisher(config.mqtt)

    def set_mqtt_client(self, client: mqtt.Client) -> None:
        self._publisher.set_client(client)
        logger.info("MQTT client set in publisher.")

    def set_tracer(self, tracer: Tracer) -> None:
        self._tracer = tracer or get_tracer()
        logger.info("Tracer set.")

    @property
    def tracer(self) -> Tracer:
        return self._tracer or get_tracer()

    async def _simulate_device(self, device_id: str) -> None:
        logger.debug(f"[{device_id}] Simulation started.")
        try:
            while True:
                await self._simulate_once(device_id)
                await asyncio.sleep(self._device_manager.frequency_sec)
        except asyncio.CancelledError:
            logger.info(f"[{device_id}] Simulation cancelled.")
            raise

    async def _simulate_once(self, device_id: str) -> None:
        with get_span_context(self.tracer, "publish_sensor_data") as span:
            payload = self._payload_generator(device_id)
            self._publisher.publish(device_id, payload)

            span.set_attribute("device_id", device_id)
            span.set_attribute("payload.size", len(str(payload)))
            span.set_attribute("mqtt.topic", self._publisher.topic)
            span.set_attribute("mqtt.broker", self._publisher.host)


    def start_device(self, device_id: str) -> None:
        if self._device_manager.is_device_running(device_id):
            return
        task = asyncio.create_task(self._simulate_device(device_id))
        self._device_manager.start_task(device_id, task)

    async def start(self, count: int) -> None:
        await self._device_manager.stop_all()
        for i in range(min(count, self._device_manager.max_devices)):
            device_id = self._device_manager.generate_device_id(i)
            self.start_device(device_id)
        await asyncio.sleep(0.01)

    async def scale(self, count: int) -> None:
        await self.start(count)

    async def stop_device(self, device_id: str) -> None:
        await self._device_manager.stop_task(device_id)

    async def stop_all(self) -> None:
        await self._device_manager.stop_all()

    def current_count(self) -> int:
        return self._device_manager.current_count()

    def running_ids(self) -> list[str]:
        return self._device_manager.running_ids()

    def is_device_running(self, device_id: str) -> bool:
        return self._device_manager.is_device_running(device_id)

    @property
    def running(self) -> bool:
        return self._device_manager.running
