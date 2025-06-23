import asyncio

import pytest

from simulator.configs import AppConfig, MQTTConfig, SimulationConfig
from simulator.simulator import SimulatorController, default_payload
from tests.mocks import MockMQTTClient


@pytest.fixture
def simulator() -> SimulatorController:
    config = AppConfig(
        simulation=SimulationConfig(frequency_sec=2, max_devices=10),
        mqtt=MQTTConfig(host="localhost", port=1883, topic="sensor/data", qos=1),
        observability=None,
        server=None,
    )
    controller = SimulatorController(config=config, payload_generator=default_payload)
    controller.set_mqtt_client(MockMQTTClient())
    return controller


def test_generate_device_id(simulator: SimulatorController):
    assert simulator._device_manager.generate_device_id(0) == "device_000"
    assert simulator._device_manager.generate_device_id(9) == "device_009"


@pytest.mark.asyncio
async def test_start_and_stop(simulator: SimulatorController):
    await simulator.start(1)
    await asyncio.sleep(0.2)  # Ensure task runs at least once
    assert simulator.current_count() == 1
    assert simulator.is_device_running("device_000")

    await simulator.stop_device("device_000")
    assert not simulator.is_device_running("device_000")
    assert simulator.current_count() == 0


@pytest.mark.asyncio
async def test_scale_devices(simulator: SimulatorController):
    await simulator.scale(3)
    await asyncio.sleep(0.2)
    assert simulator.current_count() == 3
    assert all(simulator.is_device_running(f"device_00{i}") for i in range(3))

    await simulator.scale(1)
    await asyncio.sleep(0.2)
    assert simulator.current_count() == 1
    assert simulator.is_device_running("device_000")

    await simulator.stop_all()
    assert simulator.current_count() == 0
