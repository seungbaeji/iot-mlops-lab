import asyncio
import logging
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from iot_simulator.configs import AppConfig
from iot_simulator.main import init_app

from tests.mocks import MockMQTTClient

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    # 1. 새로운 app 인스턴스를 매 테스트마다 생성
    app = FastAPI()

    # 2. 설정 및 모의 MQTT 클라이언트로 초기화
    config = AppConfig.load("config/config.toml")
    config.observability.trace_endpoint = ""  # tracing 비활성화
    init_app(app, config, mqtt_client=MockMQTTClient())

    # 3. 테스트 클라이언트 구성
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    # 4. 테스트 종료 시 graceful shutdown
    if hasattr(app.state, "simulator"):
        await app.state.simulator.stop_all()
    await asyncio.sleep(0.05)  # 남은 task clean up


@pytest.mark.asyncio
async def test_start_devices(async_client: AsyncClient):
    response = await async_client.get("/start?count=3")
    await asyncio.sleep(0.05)  # Ensure tasks are scheduled
    data = response.json()
    assert response.status_code == 200
    assert data["status"] == "started"
    assert data["started"] == 3
    assert data["running"] == 3


@pytest.mark.asyncio
async def test_stop_devices(async_client: AsyncClient):
    await async_client.get("/start?count=3")
    response = await async_client.get("/stop")
    await asyncio.sleep(0.05)
    data = response.json()
    assert response.status_code == 200
    assert data["status"] == "stopped"
    assert data["running"] == 0


@pytest.mark.asyncio
async def test_scale_devices(async_client: AsyncClient):
    await async_client.get("/start?count=2")
    response = await async_client.get("/scale?count=6")
    await asyncio.sleep(0.05)
    data = response.json()
    assert response.status_code == 200
    assert data["status"] == "scaled up"
    assert data["added"] == 4
    assert data["running"] == 6


@pytest.mark.asyncio
async def test_status_check(async_client: AsyncClient):
    await async_client.get("/start?count=4")
    await asyncio.sleep(0.05)
    response = await async_client.get("/status")
    data = response.json()
    assert response.status_code == 200
    assert data["status"] == "running"
    assert data["count"] == 4
    assert isinstance(data["devices"], list)
    assert all(d.startswith("device_") for d in data["devices"])

    await async_client.get("/stop")
