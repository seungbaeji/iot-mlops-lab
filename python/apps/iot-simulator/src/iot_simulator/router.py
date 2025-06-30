from typing import Any

from fastapi import APIRouter, Query
from opentelemetry.trace import Span, Tracer

from iot_simulator.observability import get_span_context
from iot_simulator.simulator import SimulatorController


def create_router(
    simulator: SimulatorController,
    tracer: Tracer | None = None,
) -> APIRouter:
    router = APIRouter()

    @router.get("/start")
    async def start_simulation(count: int = Query(1, ge=1)) -> dict[str, Any]:
        with get_span_context(tracer, "router.start_devices") as span:
            count = min(count, simulator._device_manager.max_devices)
            span.set_attribute("input.count", count)

            await simulator.start(count)
            span.set_attribute("started.count", count)

            return {
                "status": "started",
                "started": count,
                "running": simulator.current_count(),
            }

    @router.get("/scale")
    async def scale_simulation(count: int = Query(0, ge=0)) -> dict[str, Any]:
        with get_span_context(tracer, "router.scale_devices") as span:
            return await _adjust_scale(simulator, count, span)

    @router.get("/stop")
    async def stop_simulation() -> dict[str, Any]:
        with get_span_context(tracer, "router.stop_devices"):
            await simulator.stop_all()
            return {"status": "stopped", "running": 0}

    @router.get("/status")
    async def get_status() -> dict[str, Any]:
        with get_span_context(tracer, "router.status_devices") as span:
            count = simulator.current_count()
            runnings = simulator.running_ids()

            span.set_attribute("status.count", count)

            return {
                "status": "running" if simulator.running else "stopped",
                "count": count,
                "devices": runnings,
            }

    return router


async def _adjust_scale(
    simulator: SimulatorController,
    target_count: int,
    span: Span,
) -> dict[str, Any]:
    max_count = simulator._device_manager.max_devices
    target_count = min(target_count, max_count)
    current = simulator.current_count()

    span.set_attribute("scale.target_count", target_count)
    span.set_attribute("scale.current_count", current)

    if target_count > current:
        await simulator.scale(target_count)
        result = {
            "status": "scaled up",
            "added": target_count - current,
            "running": simulator.current_count(),
        }
    elif target_count < current:
        await simulator.scale(target_count)
        result = {
            "status": "scaled down",
            "removed": current - target_count,
            "running": simulator.current_count(),
        }
    else:
        result = {"status": "unchanged", "running": current}

    span.set_attribute("scale.result", str(result["status"]))
    return result
