# Fase 3.3 – Despliegue del Sistema (Free Tier): Plan de Implementación

> **Para agentes:** SUB-SKILL REQUERIDA: usar superpowers:executing-plans (nativo) o superpowers:subagent-driven-development para ejecutar tarea por tarea. Los pasos usan checkboxes (`- [ ]`).
>
> **Nota de proceso:** a diferencia de los planes de 3.1/3.2, no todas las tareas son TDD — las Tareas 1, 3 y 4 son artefactos de infraestructura/documentación (Dockerfile, runbooks) que este entorno no puede ejecutar ni probar automáticamente (sin Docker local, sin acceso a los dashboards de Koyeb/Cloudflare). Cada una lo dice explícitamente en su encabezado.

**Goal:** Backend desplegable en Koyeb vía Dockerfile con CORS habilitado para Cloudflare Pages, Neon de producción migrado, y los dos frontends (panel + PWA) listos para publicarse como dos proyectos de Cloudflare Pages.

**Architecture:** Sin cambios de arquitectura de aplicación — solo empaquetado (Dockerfile multi-stage), una capa de middleware (CORS) y artefactos de configuración de plataforma (`_redirects`, runbooks). Ver spec para el detalle completo.

**Tech Stack:** Docker (multi-stage, `python:3.12-slim`), `starlette.middleware.cors.CORSMiddleware` (ya viene con FastAPI), sin dependencias nuevas.

**Spec:** `docs/superpowers/specs/2026-09-22-fase-3-3-despliegue-design.md` (y `CLAUDE.md` sección 3).

## Global Constraints

- Presupuesto S/. 0.00: solo Neon/Koyeb/Cloudflare Pages free tier, sin servicios adicionales.
- Koyeb: 512 MB RAM, 0.1 vCPU → `uvicorn --workers 1` obligatorio.
- `CORSMiddleware`: `allow_origin_regex=r"^https://.*\.pages\.dev$"` + `allow_origins=["http://localhost:5173", "http://localhost:5174"]`, `allow_credentials=False` (JWT por header, no cookies).
- La migración de Neon producción la ejecuta el usuario en su propia terminal con el comando de la Tarea 2; el agente nunca ve ni pide la cadena de conexión de producción.
- Sin Docker local en este entorno: el Dockerfile se construye con el máximo cuidado y se revisa estáticamente, pero su primera ejecución real es del usuario o del build log de Koyeb — declarado, no simulado como si hubiera pasado una prueba que no corrió.
- Dos proyectos de Cloudflare Pages (uno por `frontend/`, uno por `pwa/`), cada uno con su propio `_redirects` y la misma variable `VITE_API_URL`.
- Sin GitHub Actions nuevo: Koyeb y Cloudflare Pages ya disparan build+deploy nativamente al conectar el repo.

## Review Focus

1. Un origen no listado en CORS (ej. un dominio de phishing que copie el panel) no debe recibir `Access-Control-Allow-Origin` — el navegador debe bloquear la respuesta.
2. `localhost:5173` y `localhost:5174` deben seguir funcionando en desarrollo después de agregar CORS (no romper el flujo local que usan `frontend/` y `pwa/` hoy).
3. Agregar `CORSMiddleware` no debe cambiar el comportamiento de ningún endpoint existente para peticiones sin header `Origin` (Postman, `httpx` en los tests, curl) — CORS es una instrucción para navegadores, no una capa de autorización.
4. El Dockerfile no debe incluir `.env`, `tests/`, ni credenciales de ningún tipo en la imagen final (verificable por inspección del `.dockerignore` y de las etapas `COPY`).
5. El comando de migración de producción (Tarea 2) debe ser ejecutable literalmente por copiar-pegar, con un único marcador a reemplazar (`<cadena-de-conexion-pooler-de-produccion>`) — cualquier ambigüedad ahí es un error costoso (podría migrar la BD equivocada).

## Estructura de archivos

```
backend/
  Dockerfile                  nuevo — build multi-stage
  .dockerignore                nuevo
  app/main.py                  + CORSMiddleware
  tests/test_cors.py           nuevo
docs/deploy/
  koyeb.md                     nuevo — runbook: Dockerfile, healthcheck, variables de entorno, migracion
  cloudflare-pages.md          nuevo — runbook: dos proyectos, root directory, build command, VITE_API_URL
frontend/public/_redirects     nuevo
pwa/public/_redirects          nuevo
```

---

## Tarea 0: CORS — `CORSMiddleware`

**Files:**
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_cors.py`

**Interfaces:**
- Produces: respuestas HTTP con `Access-Control-Allow-Origin` reflejando el origen cuando corresponde.

- [ ] **Paso 1: Escribir los tests que fallan**

```python
# backend/tests/test_cors.py
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
```

- [ ] **Paso 2: Correr y verificar que fallan**

Run: `cd backend && .venv\Scripts\python -m pytest -q tests/test_cors.py`
Expected: FAIL — sin `CORSMiddleware`, ninguna respuesta trae `access-control-allow-origin`, y `OPTIONS /clientes` da 405 (no hay handler de preflight)

- [ ] **Paso 3: Implementación**

```python
# backend/app/main.py — agregar tras crear `app`
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https://.*\.pages\.dev$",
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

(Se agrega inmediatamente después de `app = FastAPI(...)`, antes de registrar los routers — el orden de middlewares no afecta aquí, pero mantiene `main.py` legible de arriba a abajo: app → middlewares → routers → handlers.)

- [ ] **Paso 4: Correr y verificar que pasan**

Run: `cd backend && .venv\Scripts\python -m pytest -q tests/test_cors.py`
Expected: PASS 7/7 (4 orígenes parametrizados + no-permitido + preflight + sin-Origin)

- [ ] **Paso 5: Suite completa y commit**

```bash
cd backend && .venv\Scripts\python -m pytest -q
git add backend/app/main.py backend/tests/test_cors.py
git commit -m "feat(backend): CORS para Cloudflare Pages y desarrollo local"
```

Expected: suite completa sigue en 199+7 = 206 passed, sin regresiones (Review Focus 3).

## Tarea 1: Dockerfile optimizado (no-TDD — infraestructura)

**Files:**
- Create: `backend/Dockerfile`
- Create: `backend/.dockerignore`

**Nota:** sin Docker local en este entorno, este paso no se "verifica en verde" como los anteriores. Se revisa por inspección (Review Focus 4) y su primera ejecución real es del usuario o de Koyeb.

- [ ] **Paso 1: Escribir `.dockerignore`**

```
# backend/.dockerignore
.venv/
__pycache__/
**/__pycache__/
.pytest_cache/
tests/
.env
.env.*
!.env.example
*.egg-info/
.git/
alembic/versions/__pycache__/
```

- [ ] **Paso 2: Escribir el Dockerfile**

```dockerfile
# backend/Dockerfile
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
```

- [ ] **Paso 3: Revisión estática contra el Review Focus 4**

Verificar a mano (no hay test automatizado posible sin Docker):
- `.dockerignore` excluye `.env`, `tests/`, `.git/` → confirmado por inspección de línea arriba.
- Ningún `COPY` de la etapa final copia `tests/`, `.env`, ni `.git/` → confirmado (solo copia `app`, `alembic`, `alembic.ini`, `pyproject.toml`, y el venv de la etapa `builder`).
- El healthcheck y el `CMD` usan `$PORT`, nunca un puerto fijo hardcodeado.

- [ ] **Paso 4: Commit**

```bash
git add backend/Dockerfile backend/.dockerignore
git commit -m "feat(backend): Dockerfile multi-stage optimizado para Koyeb (512MB/0.1vCPU)"
```

- [ ] **Paso 5 (usuario, fuera de este plan): validar localmente si tiene Docker**

```bash
cd backend
docker build -t fildlab-backend .
docker run --rm -p 8000:8000 -e DATABASE_URL="<pooler-de-test>" -e JWT_SECRET="una-clave-local-de-32-caracteres-o-mas" fildlab-backend
curl http://localhost:8000/api/v1/healthz
```

Expected: `{"status":"ok"}`. Si el usuario no tiene Docker instalado, este paso se omite y la primera prueba real es el build log de Koyeb (Tarea 3).

## Tarea 2: Neon — migración de producción (manual, usuario)

**Nota:** esta tarea no la ejecuta el agente. Se documenta aquí porque es parte del plan de despliegue y su comando exacto debe quedar registrado.

- [ ] El usuario abre una terminal en `backend/`, con el venv activo (`.venv\Scripts\python` disponible), y corre:

```powershell
.venv\Scripts\python -m alembic -x db_url="<cadena-de-conexion-pooler-de-produccion>" upgrade head
```

Reemplazando `<cadena-de-conexion-pooler-de-produccion>` por la cadena real de la rama `main` de Neon **con el sufijo `-pooler`** en el host — la misma forma que ya usa `DATABASE_URL_TEST` en `backend/.env`, pero apuntando a la base de datos de producción, nunca a la de test.

- [ ] Verificar la salida: debe terminar con una línea `Running upgrade  -> 194ec320cb67, esquema inicial fase 3.1` (mismo id de revisión ya usado en 3.1) y sin errores.

- [ ] El usuario confirma en el chat que la migración corrió sin errores antes de continuar a la Tarea 3 — Koyeb no debe arrancar contra un esquema de producción vacío.

## Tarea 3: Koyeb — runbook de despliegue (no-TDD — documentación)

**Files:**
- Create: `docs/deploy/koyeb.md`

- [ ] **Paso 1: Escribir el runbook**

```markdown
# Desplegar el backend en Koyeb

## Prerrequisito
La Tarea 2 (migración de Neon producción) debe estar completa antes de este paso.

## 1. Crear el servicio
1. En el dashboard de Koyeb: **Create App** → **GitHub** → seleccionar el repo `Fildlab`.
2. Método de build: **Dockerfile**.
3. Dockerfile path: `backend/Dockerfile`.
4. Build context / Work directory: `backend/`.
5. Branch: `main`. Auto-deploy: activado (cada `git push` a `main` redepliega).

## 2. Variables de entorno (Koyeb → Settings → Environment variables)

| Variable | Valor |
|---|---|
| `DATABASE_URL` | Cadena de conexión del pooler de Neon, rama `main` (producción) |
| `JWT_SECRET` | ≥32 caracteres, distinto del usado en tests — generar con `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `JWT_EXPIRE_MIN` | Opcional. Si se omite, default 60. |

`PORT` no se configura manualmente: Koyeb la inyecta automáticamente y el `CMD` del Dockerfile ya la respeta.

## 3. Healthcheck
Koyeb → Settings → Health checks: método `HTTP`, path `/api/v1/healthz`, puerto el mismo del servicio. Este endpoint no requiere autenticación ni toca la base de datos (mitiga cold starts, RNF-01).

## 4. Crear el primer usuario Gerencia (una sola vez)
Koyeb → **One-off Jobs** (no el servicio web persistente) con el mismo Dockerfile, override del `CMD`:
```
python -m app.scripts.crear_gerente
```
con las variables adicionales `GERENTE_NOMBRE`, `GERENTE_EMAIL`, `GERENTE_PASSWORD` configuradas solo para ese job (no en el servicio persistente).

## 5. Verificación post-deploy
- `curl https://<tu-servicio>.koyeb.app/api/v1/healthz` → `{"status":"ok"}`.
- `curl -X POST https://<tu-servicio>.koyeb.app/api/v1/auth/login -H "Content-Type: application/json" -d "{\"email\":\"...\",\"password\":\"...\"}"` con el usuario Gerencia recién creado → debe devolver un `access_token`.
```

- [ ] **Paso 2: Commit**

```bash
git add docs/deploy/koyeb.md
git commit -m "docs: runbook de despliegue del backend en Koyeb"
```

## Tarea 4: Cloudflare Pages — `_redirects` y runbook (no-TDD — configuración/documentación)

**Files:**
- Create: `frontend/public/_redirects`
- Create: `pwa/public/_redirects`
- Create: `docs/deploy/cloudflare-pages.md`

- [ ] **Paso 1: Escribir los `_redirects`**

```
# frontend/public/_redirects
/*  /index.html  200
```

```
# pwa/public/_redirects
/*  /index.html  200
```

(Idéntico en ambos: cada proyecto es una SPA con ruteo en cliente; sin esto, recargar cualquier ruta que no sea `/` da 404 en Cloudflare Pages.)

- [ ] **Paso 2: Verificar que Vite copia `public/_redirects` al build**

```bash
cd frontend && npm run build && Get-Content dist\_redirects
cd ..\pwa && npm run build && Get-Content dist\_redirects
```

Expected: ambos comandos imprimen `/*  /index.html  200` — confirma que Vite copió el archivo de `public/` a `dist/` sin transformarlo (Vite copia `public/` tal cual por diseño, así que esto es una verificación, no una implementación nueva).

- [ ] **Paso 3: Escribir el runbook**

```markdown
# Desplegar frontend/ y pwa/ en Cloudflare Pages (dos proyectos)

## Proyecto 1 — Panel administrativo
1. Cloudflare dashboard → **Workers & Pages** → **Create** → **Pages** → **Connect to Git** → repo `Fildlab`.
2. **Root directory**: `frontend`.
3. **Build command**: `npm run build`.
4. **Build output directory**: `dist`.
5. Variables de entorno (Settings → Environment variables): `VITE_API_URL` = URL pública del servicio de Koyeb (sin `/` final).
6. Branch de producción: `main`.

## Proyecto 2 — PWA de campo
Mismos pasos, con:
- **Root directory**: `pwa`.
- Mismo `VITE_API_URL`.

## Verificación post-deploy (ambos proyectos)
- La URL `*.pages.dev` asignada carga la pantalla de login.
- Navegar a una ruta que no exista en el historial del navegador (pegar la URL de una pantalla interna directamente) y recargar: debe seguir mostrando la app, no un 404 de Cloudflare — confirma que `_redirects` se aplicó.
- Solo para el proyecto de la PWA: en un navegador móvil (o Chrome DevTools → Application → Manifest), confirmar que aparece la opción "Agregar a pantalla de inicio" / "Instalar" — confirma que `manifest.webmanifest` y `sw.js` se sirvieron correctamente.
- Iniciar sesión contra el backend real de Koyeb desde ambas URLs de Cloudflare Pages — confirma que CORS (Tarea 0) permite el origen `*.pages.dev` real, no solo el patrón en el test.
```

- [ ] **Paso 4: Commit**

```bash
git add frontend/public/_redirects pwa/public/_redirects docs/deploy/cloudflare-pages.md
git commit -m "feat: _redirects para SPA en Cloudflare Pages + runbook de despliegue de los dos proyectos"
```

## Tarea 5: Cierre de fase

- [ ] `pytest` completo del backend en verde (incluye los 7 tests de CORS de la Tarea 0), sin warnings.
- [ ] Confirmación del usuario de que corrió la migración de la Tarea 2 contra Neon producción.
- [ ] Confirmación del usuario de que conectó Koyeb (Tarea 3) y Cloudflare Pages ×2 (Tarea 4) siguiendo los runbooks, con los checklists de verificación post-deploy completos.
- [ ] Marcar 3.3.1, 3.3.2, 3.3.3 y 3.3 en la sección 7 de `CLAUDE.md` — **solo después** de que el usuario confirme que los tres despliegues externos están arriba (a diferencia de 3.1/3.2, aquí "completo" depende de acciones fuera de este repo que el agente no puede verificar por sí mismo).
- [ ] Revisión final de la rama con `requesting-code-review` (modelo más capaz) sobre lo que sí es código de este repo (CORS, Dockerfile, `_redirects`) — el Review Focus de este plan sirve de guía.

## Nota de alcance del plan

Las Tareas 1, 3 y 4 no siguen TDD porque no son código de aplicación probable en este entorno (Dockerfile sin Docker local; runbooks y config de dashboard sin acceso a Koyeb/Cloudflare). Se compensan con revisión estática explícita (Tarea 1) y checklists de verificación post-deploy que el usuario ejecuta (Tareas 3 y 4) — la disciplina de "no marcar completo sin evidencia" se traslada de "test en verde" a "el usuario confirma que lo verificó", declarado así en la Tarea 5.
