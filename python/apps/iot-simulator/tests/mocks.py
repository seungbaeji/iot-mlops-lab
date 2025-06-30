from typing import Any


class MockMQTTClient:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.published = []

    def connect(self, *args: Any, **kwargs: Any) -> None:
        pass  # no-op

    def loop_start(self) -> None:
        pass  # no-op

    def publish(self, topic: str, payload: str, qos: int) -> None:
        self.published.append((topic, payload, qos))

    @property
    def host(self) -> str:
        return "localhost"
