# from unittest.mock import patch

# import pytest


# # Prometheus port 충돌 방지용 mock fixture
# @pytest.fixture(autouse=True)
# def mock_prometheus_port():
#     with patch("simulator.main.start_http_server"):
#         yield


# @pytest.fixture(autouse=True)
# def disable_tracing():
#     with patch("simulator.main.init_tracing"):
#         yield
