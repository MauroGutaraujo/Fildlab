from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.api.v1 import auth, clientes, contratos, equipos, health, inventario, liquidacion, ventas

app = FastAPI(title="Fildlab API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https://.*\.pages\.dev$",
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(clientes.router, prefix="/api/v1")
app.include_router(contratos.router, prefix="/api/v1")
app.include_router(inventario.router, prefix="/api/v1")
app.include_router(ventas.router, prefix="/api/v1")
app.include_router(equipos.router, prefix="/api/v1")
app.include_router(liquidacion.router, prefix="/api/v1")


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    """Red de seguridad: una carrera entre dos peticiones (comprobar-y-luego-insertar) no
    debe llegar como 500. La comprobación explícita en cada endpoint sigue siendo el camino
    rápido; esto solo atrapa lo que se le escapa bajo concurrencia real."""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "El registro ya existe o entra en conflicto con datos relacionados"},
    )
