from iot_subscriber.config import AppConfig


def test_app_config_load(tmp_path):
    # 샘플 TOML 파일 생성
    toml_content = """
[mqtt]
host  = "localhost"
port  = 1883
qos   = 0
topic = "sensors/#"

[subscriber]
batch_size            = 1000
error_retry_delay_sec = 5
flush_interval        = 3
max_batch_size        = 10000
min_batch_size        = 500
mqtt_reconn_delay_sec = 5

[observability]
prometheus_port = 8001
service_name    = "iot-subscriber"
trace_endpoint  = "http://localhost:4318/v1/traces"

[redis]
host        = "localhost"
maxlen      = 100000               # 원하는 메시지 최대 개수
port        = 6379
stream_name = "sensor_data_stream"
"""
    config_path = tmp_path / "config.toml"
    config_path.write_text(toml_content)

    config = AppConfig.load(config_path)
    assert config.mqtt.host == "localhost"
    assert config.subscriber.batch_size == 1000
    assert config.subscriber.flush_interval == 3
    assert config.subscriber.mqtt_reconn_delay_sec == 5
    assert config.subscriber.error_retry_delay_sec == 5
    assert config.observability.prometheus_port == 8001
    assert config.observability.service_name == "iot-subscriber"
    assert config.observability.trace_endpoint == "http://localhost:4318/v1/traces"
    assert config.redis.host == "localhost"
    assert config.redis.maxlen == 100000
    assert config.redis.stream_name == "sensor_data_stream"
