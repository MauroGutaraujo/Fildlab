from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.api.v1 import analytics, auth, clientes, componentes, contratos, equipos, health, historial_rul, inventario, liquidacion, ventas
from app.core.config import Settings, get_settings
from app.core.password_workers import BoundedPasswordVerifier
from app.core.request_limits import LoginLimiter, RequestLimitsMiddleware


async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "El registro ya existe o entra en conflicto con datos relacionados"},
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    application = FastAPI(title="Fildlab API", version="0.1.0")
    application.state.password_verifier = BoundedPasswordVerifier(settings.password_verify_concurrency)
    application.state.login_limiter = LoginLimiter(
        settings.login_attempts_per_window,
        settings.login_global_attempts_per_window,
        settings.login_window_seconds,
    )
    application.add_middleware(RequestLimitsMiddleware, settings=settings, limiter=application.state.login_limiter)
    # CORS wraps ingress failures too, so authorized clients can display 413/429.
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    for module in (health, analytics, auth, clientes, contratos, inventario, ventas, historial_rul, equipos, componentes, liquidacion):
        application.include_router(module.router, prefix="/api/v1")
    application.add_exception_handler(IntegrityError, integrity_error_handler)
    return application


app = create_app()
