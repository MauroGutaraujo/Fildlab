"""Run expensive password checks without blocking the loop or queuing unbounded work."""
import asyncio
from collections.abc import Callable

from fastapi import HTTPException

from app.core.security import verify_password


class BoundedPasswordVerifier:
    def __init__(self, concurrency: int, operation: Callable[[str, str], bool] = verify_password):
        self.concurrency = concurrency
        self.operation = operation
        self.active: set[asyncio.Task] = set()

    async def verify(self, plain: str, hashed: str) -> bool:
        # Called on one event loop: admission contains no await, hence is atomic.
        if len(self.active) >= self.concurrency:
            raise HTTPException(429, "Verificación ocupada. Intente nuevamente.", headers={"Retry-After": "1"})
        task = asyncio.create_task(asyncio.to_thread(self.operation, plain, hashed))
        self.active.add(task)
        task.add_done_callback(self._finished)
        # Cancellation of an HTTP request cannot release a slot while Argon2 is
        # still consuming memory/CPU in its thread.
        return await asyncio.shield(task)

    def _finished(self, task: asyncio.Task) -> None:
        self.active.discard(task)
        if not task.cancelled():
            task.exception()  # retrieve failures even when the requester disconnected
