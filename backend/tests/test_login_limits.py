import asyncio
import importlib.util
import threading

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.core.request_limits import LoginLimiter
from app.main import create_app


def test_limiter_sliding_window_expires_and_bounds_distributed_attempts():
    now = [100.0]
    limiter = LoginLimiter(2, 3, 60, clock=lambda: now[0])
    assert limiter.retry_after("a") == 0
    assert limiter.retry_after("a") == 0
    assert limiter.retry_after("a") == 60
    assert limiter.retry_after("b") == 0
    assert limiter.retry_after("c") == 60
    now[0] = 160.0
    assert limiter.retry_after("a") == 0
    assert limiter.retry_after("b") == 0


async def test_malformed_login_attempts_are_limited_and_forwarded_headers_cannot_bypass():
    application = create_app(Settings(login_attempts_per_window=2))
    async with AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as client:
        for index in range(2):
            response = await client.post("/api/v1/auth/login", content="{", headers={"X-Forwarded-For": f"10.0.0.{index}"})
            assert response.status_code == 422
        response = await client.post("/api/v1/auth/login/", content="{", headers={
            "X-Forwarded-For": "10.0.0.200", "Origin": "https://fildlab-pwa.pages.dev",
        })
        assert response.status_code == 429
        assert int(response.headers["retry-after"]) > 0
        assert response.headers["access-control-allow-origin"] == "https://fildlab-pwa.pages.dev"
        assert (await client.get("/api/v1/healthz")).status_code == 200


async def test_password_workers_do_not_block_event_loop_and_reject_over_capacity():
    assert importlib.util.find_spec("app.core.password_workers") is not None, "Argon2 needs bounded asynchronous workers"
    from app.core.password_workers import BoundedPasswordVerifier

    started, release = threading.Event(), threading.Event()
    loop_thread = threading.get_ident()
    worker_threads = []

    def verify(plain, hashed):
        worker_threads.append(threading.get_ident())
        started.set()
        assert release.wait(2), "event loop could not release worker"
        return plain == "correct"

    verifier = BoundedPasswordVerifier(1, operation=verify)
    first = asyncio.create_task(verifier.verify("correct", "hash"))
    try:
        for _ in range(100):
            if started.is_set():
                break
            await asyncio.sleep(0.001)
        assert started.is_set()
        with pytest.raises(HTTPException) as error:
            await verifier.verify("correct", "hash")
        assert error.value.status_code == 429
        assert worker_threads == [worker_threads[0]] and worker_threads[0] != loop_thread
    finally:
        release.set()
    assert await first is True
    assert await verifier.verify("wrong", "hash") is False


async def test_cancelling_request_does_not_release_running_password_worker():
    assert importlib.util.find_spec("app.core.password_workers") is not None
    from app.core.password_workers import BoundedPasswordVerifier

    started, release = threading.Event(), threading.Event()

    def verify(plain, hashed):
        started.set()
        release.wait(2)
        return True

    verifier = BoundedPasswordVerifier(1, operation=verify)
    request = asyncio.create_task(verifier.verify("x", "hash"))
    try:
        for _ in range(100):
            if started.is_set():
                break
            await asyncio.sleep(0.001)
        assert started.is_set()
        request.cancel()
        with pytest.raises(asyncio.CancelledError):
            await request
        with pytest.raises(HTTPException) as error:
            await verifier.verify("x", "hash")
        assert error.value.status_code == 429
    finally:
        release.set()
        await asyncio.sleep(0.02)
