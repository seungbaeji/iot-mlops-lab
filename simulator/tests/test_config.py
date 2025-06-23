from simulator.configs import AppConfig


def test_config_valid_structure():
    config = AppConfig.load("config/config.toml")
    assert isinstance(config, AppConfig)
    assert isinstance(config.mqtt.port, int)
    assert 0 < config.simulation.max_devices <= 10000
    assert config.observability.service_name
