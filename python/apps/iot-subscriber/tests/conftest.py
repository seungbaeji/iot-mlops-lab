import pytest
from iot_subscriber.config import (
    AppConfig,
    MQTTConfig,
    SubscriberConfig,
    ObservabilityConfig,
    RedisConfig,
)


@pytest.fixture
def sample_config():
    return AppConfig(
        mqtt=MQTTConfig(host="localhost", port=1883, topic="test/topic"),
        subscriber=SubscriberConfig(
            batch_size=2,
            flush_interval=1,
            mqtt_reconn_delay_sec=1,
            error_retry_delay_sec=1,
        ),
        observability=ObservabilityConfig(
            prometheus_port=8001,
            service_name="iot-subscriber",
            trace_endpoint="http://localhost:4318/v1/traces",
        ),
        redis=RedisConfig(
            host="localhost",
            port=6379,
            maxlen=100000,
            stream_name="sensor_data_stream",
        ),
    )
