import pytest
from iot_subscriber.subscriber import SubscriberController


@pytest.mark.asyncio
async def test_queue_put_adds_to_queue(sample_config):
    controller = SubscriberController(sample_config)
    # Simulate a message payload as would be received from MQTT
    payload = {
        "device_id": "dev1",
        "timestamp": 1,
        "temperature": 22.5,
        "humidity": 55.0,
    }
    # Put the payload into the queue
    await controller.queue.put(payload)
    # Check that the queue size is 1
    assert controller.queue.queue.qsize() == 1
    # Optionally, check the content
    item = await controller.queue.queue.get()
    assert item["payload"] == payload
