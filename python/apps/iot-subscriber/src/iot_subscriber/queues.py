import asyncio
import time
from typing import Any

from iot_subscriber.observability import Metrics


class AsyncBatchQueueWrapper:
    def __init__(
        self,
        min_batch_size: int,
        max_batch_size: int,
        initial_batch_size: int,
    ):
        self.queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self.min_batch_size = min_batch_size
        self.max_batch_size = max_batch_size
        self.batch_size = initial_batch_size

    def _adjust_batch_size(self) -> None:
        qsize = self.queue.qsize()
        if qsize > self.batch_size * 2:
            self.batch_size = min(self.batch_size * 2, self.max_batch_size)
        elif qsize < self.batch_size // 2:
            self.batch_size = max(self.batch_size // 2, self.min_batch_size)
        Metrics.batch_size.set(self.batch_size)

    async def put(self, item: Any) -> None:
        if not (isinstance(item, dict) and "enqueued_at" in item):
            item = {"payload": item, "enqueued_at": time.monotonic()}
        else:
            item = dict(item)
            item["enqueued_at"] = time.monotonic()
        await self.queue.put(item)
        Metrics.current_queue_size.set(self.queue.qsize())

    async def get_batch(self) -> list[Any]:
        batch: list[Any] = []
        now = time.monotonic()
        while len(batch) < self.batch_size and not self.queue.empty():
            item = await self.queue.get()
            enq = item.get("enqueued_at")
            if enq is not None:
                Metrics.queue_wait_time.observe(now - enq)
            batch.append(item.get("payload", item))
        if batch:
            Metrics.batch_size.set(len(batch))
            Metrics.current_queue_size.set(self.queue.qsize())
        self._adjust_batch_size()
        return batch
