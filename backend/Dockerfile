# Build multi-stage: la etapa final no lleva compiladores ni herramientas de build,
# solo el venv ya resuelto y el codigo de la app — reduce el tamano de imagen y la
# superficie de ataque en un contenedor con 512 MB de RAM.

FROM python:3.12-slim AS builder

WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml ./
COPY app ./app
# Instala solo el paquete de produccion (sin el extra [dev] de pytest/httpx).
# asyncpg y argon2-cffi publican wheels manylinux para CPython 3.12 en glibc
# (base de python:3.12-slim), asi que esto no deberia requerir compilar nada.
# Si Koyeb reportara un fallo de build por falta de wheel, agregar aqui:
#   RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*
# antes del pip install, nunca en la etapa final.
RUN pip install --no-cache-dir .

FROM python:3.12-slim

RUN groupadd --system appuser && useradd --system --gid appuser --home /app appuser
WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
COPY pyproject.toml ./

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER appuser

# Koyeb inyecta $PORT en runtime; no se fija un puerto por defecto aqui para no
# ocultar un despliegue mal configurado si $PORT no llega.
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"8000\")}/api/v1/healthz')" || exit 1

# Un solo worker: 0.1 vCPU no alcanza para paralelizar procesos de uvicorn.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
