from fastapi import APIRouter, Query

from simulator.simulator import SimulatorController


def create_router(simulator: SimulatorController) -> APIRouter:
    router = APIRouter()

    @router.get("/start")
    async def start_simulation(count: int = Query(1, ge=1)) -> dict:
        count = min(count, simulator._device_manager.max_devices)
        await simulator.start(count)
        return {
            "status": "started",
            "started": count,
            "running": simulator.current_count(),
        }

    @router.get("/scale")
    async def scale_simulation(count: int = Query(0, ge=0)) -> dict:
        return await _adjust_scale(simulator, count)

    @router.get("/stop")
    async def stop_simulation() -> dict:
        await simulator.stop_all()
        return {"status": "stopped", "running": 0}

    @router.get("/status")
    async def get_status() -> dict:
        return {
            "status": "running" if simulator.running else "stopped",
            "count": simulator.current_count(),
            "devices": simulator.running_ids(),
        }

    return router


async def _adjust_scale(simulator: SimulatorController, target_count: int) -> dict:
    max_count = simulator._device_manager.max_devices
    target_count = min(target_count, max_count)
    current = simulator.current_count()

    if target_count > current:
        await simulator.scale(target_count)
        return {
            "status": "scaled up",
            "added": target_count - current,
            "running": simulator.current_count(),
        }
    elif target_count < current:
        await simulator.scale(target_count)
        return {
            "status": "scaled down",
            "removed": current - target_count,
            "running": simulator.current_count(),
        }

    return {"status": "unchanged", "running": current}
