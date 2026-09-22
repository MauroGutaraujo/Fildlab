import pytest


@pytest.mark.parametrize("origen", [
    "https://fildlab-panel.pages.dev",
    "https://algo-random-12ab.fildlab-pwa.pages.dev",
    "http://localhost:5173",
    "http://localhost:5174",
])
async def test_cors_refleja_origenes_permitidos(client, origen):
    r = await client.get("/api/v1/healthz", headers={"Origin": origen})
    assert r.headers.get("access-control-allow-origin") == origen


async def test_cors_no_refleja_origen_no_permitido(client):
    r = await client.get("/api/v1/healthz", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in {k.lower() for k in r.headers.keys()}


async def test_cors_preflight_permite_authorization(client):
    r = await client.options(
        "/api/v1/clientes",
        headers={
            "Origin": "https://fildlab-panel.pages.dev",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert r.status_code in (200, 204)
    assert r.headers.get("access-control-allow-origin") == "https://fildlab-panel.pages.dev"


async def test_sin_header_origin_endpoints_siguen_funcionando_igual(client, gerente_h):
    """CORS no es autorizacion: una peticion sin Origin (curl, httpx de los propios tests,
    Postman) debe comportarse exactamente igual que antes de agregar el middleware."""
    r = await client.get("/api/v1/clientes", headers=gerente_h)
    assert r.status_code == 200
