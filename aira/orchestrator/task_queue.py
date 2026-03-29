"""AIRA module: orchestrator/task_queue.py"""

import asyncio
import heapq
import itertools
from datetime import datetime
from typing import Any, Awaitable, Callable

from models.agent_task import AgentTask


class AsyncTaskQueue:
    def __init__(self) -> None:
        self._queue: asyncio.Queue[tuple[Callable[..., Awaitable[Any]], tuple[Any, ...], dict[str, Any]]] = asyncio.Queue()

    async def put(self, fn: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any) -> None:
        await self._queue.put((fn, args, kwargs))

    async def run_once(self) -> Any:
        fn, args, kwargs = await self._queue.get()
        try:
            return await fn(*args, **kwargs)
        finally:
            self._queue.task_done()

    async def drain(self) -> None:
        while not self._queue.empty():
            await self.run_once()

    def size(self) -> int:
        return self._queue.qsize()


class PriorityTaskQueue:
    def __init__(self) -> None:
        self._heap: list[tuple[int, float, int, AgentTask]] = []
        self._counter = itertools.count()

    def add_task(self, task: AgentTask, priority: int) -> None:
        normalized_priority = max(1, min(10, int(priority)))
        enqueue_time = datetime.utcnow().timestamp()
        heapq.heappush(self._heap, (normalized_priority, enqueue_time, next(self._counter), task))

    def get_next_task(self) -> AgentTask | None:
        if not self._heap:
            return None
        _, _, _, task = heapq.heappop(self._heap)
        return task

    def get_queue_status(self) -> dict[str, Any]:
        tasks_by_priority: dict[str, int] = {str(priority): 0 for priority in range(1, 11)}
        oldest_task_age_seconds = 0.0

        if self._heap:
            now_ts = datetime.utcnow().timestamp()
            oldest_enqueue_ts = min(entry[1] for entry in self._heap)
            oldest_task_age_seconds = max(0.0, now_ts - oldest_enqueue_ts)
            for priority, _, _, _ in self._heap:
                key = str(priority)
                tasks_by_priority[key] = tasks_by_priority.get(key, 0) + 1

        return {
            "total_tasks": len(self._heap),
            "tasks_by_priority": tasks_by_priority,
            "oldest_task_age_seconds": round(oldest_task_age_seconds, 3),
        }


async def run_parallel_tasks(tasks: list[AgentTask], orchestrator) -> list[AgentTask]:
    async def _run_single(task: AgentTask) -> AgentTask:
        try:
            return await orchestrator.dispatch(task.agent_name, task)
        except Exception as exc:
            task.status = "failed"
            task.error_message = str(exc)
            task.completed_at = datetime.utcnow()
            return task

    if not tasks:
        return []

    results = await asyncio.gather(*[_run_single(task) for task in tasks], return_exceptions=True)
    completed: list[AgentTask] = []

    for idx, result in enumerate(results):
        if isinstance(result, Exception):
            failed_task = tasks[idx]
            failed_task.status = "failed"
            failed_task.error_message = str(result)
            failed_task.completed_at = datetime.utcnow()
            completed.append(failed_task)
        else:
            completed.append(result)

    return completed
