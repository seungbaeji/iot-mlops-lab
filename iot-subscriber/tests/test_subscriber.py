import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from iot_subscriber.subscriber import SubscriberController


@pytest.mark.asyncio
async def test_handle_message_adds_to_buffer(sample_config):
    controller = SubscriberController(sample_config)
    controller.buffer = MagicMock()
    message = MagicMock()
    message.payload.decode.return_value = (
        '{"device_id": "dev1", "timestamp": 1, "temperature": 22.5, "humidity": 55.0}'
    )
    message.topic = "test/topic"

    await controller.handle_message(message)
    assert controller.buffer.add.called
