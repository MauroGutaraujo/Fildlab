from fastapi import FastAPI

from app.api.v1 import auth, clientes, contratos, equipos, health, inventario, ventas

app = FastAPI(title="Fildlab API", version="0.1.0")
app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(clientes.router, prefix="/api/v1")
app.include_router(contratos.router, prefix="/api/v1")
app.include_router(inventario.router, prefix="/api/v1")
app.include_router(ventas.router, prefix="/api/v1")
app.include_router(equipos.router, prefix="/api/v1")
