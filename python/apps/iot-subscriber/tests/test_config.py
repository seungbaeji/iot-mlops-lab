from iot_subscriber.config import AppConfig


def test_app_config_load(tmp_path):
    # 샘플 TOML 파일 생성
    toml_content = """
[mqtt]
host = "localhost"
port = 1883
topic = "test/topic"

[database]
name = "testdb"
user = "test"
password = "test"
host = "localhost"
port = 5432

[subscriber]
batch_size = 2
flush_interval = 1
mqtt_reconn_delay_sec = 1
error_retry_delay_sec = 1
"""
    config_path = tmp_path / "config.toml"
    config_path.write_text(toml_content)

    config = AppConfig.load(config_path)
    assert config.mqtt.host == "localhost"
    assert config.database.name == "testdb"
    assert config.subscriber.batch_size == 2
