"""Per-process ingress controls; multi-worker deployments also need edge limits."""
import asyncio
import math
import time
from collections import deque

from starlette.responses import JSONResponse

from app.core.config import Settings


class LoginLimiter:
    """Sliding windows, bounded by the global request budget, using the ASGI peer.

    Forwarded headers are deliberately not parsed here. Only a trusted reverse
    proxy/server configuration should replace scope['client'].
    """

    def __init__(self, per_client: int, global_limit: int, window: float, clock=time.monotonic):
        self.per_client, self.global_limit, self.window = per_client, global_limit, window
        self.clock = clock
        self.clients: dict[str, deque[float]] = {}
        self.total: deque[float] = deque()

    def retry_after(self, client: str) -> int:
        now = self.clock()
        cutoff = now - self.window
        while self.total and self.total[0] <= cutoff:
            self.total.popleft()
        for key in list(self.clients):
            queue = self.clients[key]
            while queue and queue[0] <= cutoff:
                queue.popleft()
            if not queue:
                del self.clients[key]
        queue = self.clients.get(client)
        if len(self.total) >= self.global_limit:
            return max(1, math.ceil(self.total[0] + self.window - now))
        if queue is not None and len(queue) >= self.per_client:
            return max(1, math.ceil(queue[0] + self.window - now))
        if queue is None:
            queue = self.clients[client] = deque()
        queue.append(now)
        self.total.append(now)
        return 0


class RequestLimitsMiddleware:
    def __init__(self, app, settings: Settings, limiter: LoginLimiter):
        self.app, self.settings, self.limiter = app, settings, limiter

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        if scope["method"] == "POST" and scope["path"].rstrip("/") == "/api/v1/auth/login":
            peer = scope.get("client")
            retry = self.limiter.retry_after(peer[0] if peer else "unknown")
            if retry:
                return await JSONResponse(
                    {"detail": "Demasiados intentos. Intente nuevamente más tarde."},
                    status_code=429, headers={"Retry-After": str(retry)},
                )(scope, receive, send)
        limit = self.settings.max_request_body_bytes
        for key, value in scope.get("headers", []):
            if key.lower() == b"content-length":
                try:
                    length = int(value)
                    if length < 0:
                        raise ValueError
                except ValueError:
                    return await JSONResponse({"detail": "Content-Length inválido"}, status_code=400)(scope, receive, send)
                if length > limit:
                    return await self._too_large(scope, receive, send)
        body = bytearray()
        try:
            async with asyncio.timeout(self.settings.request_body_timeout_seconds):
                while True:
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        return
                    chunk = message.get("body", b"")
                    if len(body) + len(chunk) > limit:
                        return await self._too_large(scope, receive, send)
                    body.extend(chunk)
                    if not message.get("more_body", False):
                        break
        except TimeoutError:
            return await JSONResponse({"detail": "Tiempo de recepción agotado"}, status_code=408)(scope, receive, send)

        delivered = False

        async def bounded_receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, bounded_receive, send)

    async def _too_large(self, scope, receive, send):
        await JSONResponse({"detail": "El cuerpo excede el límite permitido"}, status_code=413)(scope, receive, send)
