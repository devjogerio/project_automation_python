import asyncio
import time

from src.gui.async_executor import AsyncExecutor


def test_async_executor_runs_coro_and_calls_callback() -> None:
    results: list[str] = []
    exec = AsyncExecutor()

    async def coro() -> str:
        await asyncio.sleep(0.01)
        return "ok"

    def cb(res: object) -> None:
        results.append(str(res))

    exec.submit(coro(), cb)
    time.sleep(0.05)
    exec.shutdown()

    assert results == ["ok"]
