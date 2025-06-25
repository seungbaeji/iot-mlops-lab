import pytest

from iot_subscriber.config import (AppConfig, DatabaseConfig, MQTTConfig,
                                   SubscriberConfig)


@pytest.fixture
def sample_config():
    return AppConfig(
        mqtt=MQTTConfig(host="localhost", port=1883, topic="test/topic"),
        database=DatabaseConfig(
            name="testdb", user="test", password="test", host="localhost", port=5432
        ),
        subscriber=SubscriberConfig(
            batch_size=2,
            flush_interval=1,
            mqtt_reconn_delay_sec=1,
            error_retry_delay_sec=1,
        ),
        observability=None,
    )
