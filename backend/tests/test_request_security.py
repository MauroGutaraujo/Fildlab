from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_unrelated_cloudflare_project_is_not_an_allowed_origin():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.options("/api/v1/auth/login", headers={
            "Origin": "https://attacker-project.pages.dev",
            "Access-Control-Request-Method": "POST",
        })
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


async def test_oversize_body_rejected_before_route_or_database():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/does-not-exist", content=b"x" * (2 * 1024 * 1024 + 1))
    assert response.status_code == 413


async def test_chunked_oversize_body_cannot_bypass_limit():
    async def chunks():
        for _ in range(3):
            yield b"x" * (1024 * 1024)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/does-not-exist", content=chunks())
    assert response.status_code == 413
