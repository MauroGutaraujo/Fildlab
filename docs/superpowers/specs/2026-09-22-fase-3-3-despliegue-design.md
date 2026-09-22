# Fase 3.3 — Despliegue del Sistema (Free Tier): Diseño

**Estado:** Aprobado por el usuario en brainstorming (2026-09-22). Listo para `writing-plans`.

## 1. Propósito y alcance

Llevar la Plataforma Web Central (3.1) y la PWA de Campo (3.2) a producción bajo presupuesto S/. 0.00, usando exclusivamente los free tiers ya elegidos en `CLAUDE.md` sección 3: Neon (BD), Koyeb (API), Cloudflare Pages (los dos frontends).

**Cubre del EDT:**
- 3.3.1 Configuración de Neon PostgreSQL (producción)
- 3.3.2 Publicar API en Koyeb con Dockerfile optimizado
- 3.3.3 Publicar PWA en Cloudflare Pages (y el panel administrativo, que comparte el mismo mecanismo)

**No cubre:**
- Crear las cuentas de Koyeb/Cloudflare — las crea el usuario.
- Conectar los repos en los dashboards de Koyeb/Cloudflare Pages — lo hace el usuario, documentado como pasos manuales del plan.
- Ejecutar `alembic upgrade head` contra Neon producción — lo ejecuta el usuario con el comando exacto que este plan produce, para no exponer la cadena de conexión de producción en la sesión.
- GitHub Actions / CI propio: Koyeb y Cloudflare Pages disparan build+deploy nativamente al hacer `git push` sobre el repo ya conectado; no se agrega un workflow adicional en 3.3.

## 2. Restricción del entorno de ejecución

**No hay Docker instalado en el entorno donde se ejecuta este plan.** El Dockerfile se escribe con el máximo cuidado posible y se revisa línea por línea, pero **no se puede construir ni correr localmente como parte de este plan**. La primera verificación real es una de estas dos, explícitas como tarea del plan:
- el usuario corre `docker build` + `docker run` + `curl /healthz` en su propia máquina antes de conectar Koyeb, o
- se confía en el primer build log de Koyeb como la prueba real.

Esto se declara aquí para que el plan no finja una cobertura de pruebas que no existe.

## 3. Arquitectura

### 3.1 Backend — `backend/Dockerfile`

Build multi-stage:
1. **`builder`** (`python:3.12-slim`): crea un venv en `/opt/venv`, instala el paquete (`pip install .`, sin extras de test) — así el compilador/headers que `pip` pueda necesitar para ruedas nativas (p. ej. `asyncpg`) no llegan a la imagen final si hay wheels precompiladas; si no las hay, se instalan build-essentials solo en esta etapa.
2. **Etapa final** (`python:3.12-slim`): copia únicamente `/opt/venv` y el código de `app/`, `alembic/`, `alembic.ini`, `pyproject.toml`. Corre como usuario no-root (`appuser`). `CMD` arranca `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1` (0.1 vCPU: un solo worker).
3. `HEALTHCHECK` del propio Dockerfile contra `/api/v1/healthz`.
4. `backend/.dockerignore`: excluye `.venv/`, `tests/`, `__pycache__/`, `.pytest_cache/`, `.env`, `alembic/versions/__pycache__/`.

`get_settings()` (Pydantic Settings, ya construido en 3.1) lee `DATABASE_URL`/`JWT_SECRET`/`JWT_EXPIRE_MIN` de variables de entorno del proceso — Koyeb las inyecta directamente, sin necesidad de un `.env` dentro de la imagen (que de hecho el `.dockerignore` excluye a propósito).

### 3.2 CORS — `backend/app/main.py`

```python
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https://.*\.pages\.dev$",
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

- `allow_origin_regex` cubre los dos proyectos de Cloudflare Pages sin fijar el subdominio exacto (Cloudflare lo asigna y puede tener variantes de preview `*.<proyecto>.pages.dev`).
- `localhost:5173` (panel) y `:5174` (PWA) para desarrollo — ambos Vite dev servers corriendo a la vez necesitan puertos distintos.
- Sin `allow_credentials`: la app autentica con `Authorization: Bearer <jwt>`, no con cookies; activar credentials además impediría usar `allow_origin_regex` de forma abierta.

### 3.3 Neon — producción

- La rama `main` de Neon (ya existente, separada de la rama de test usada desde 3.1) es la base de datos de producción.
- Koyeb usa la cadena de conexión **con el sufijo `-pooler`** en el host (pgbouncer) — igual que ya hace `DATABASE_URL_TEST` en desarrollo; `normalize_async_url()` (`app/core/config.py`, sin cambios desde 3.1) ya sabe traducir `sslmode` y fijar `statement_cache_size=0` para el pooler.
- La migración a producción se ejecuta **una única vez, manualmente, antes del primer despliegue** — nunca en el arranque del contenedor (dos instancias arrancando a la vez bajo un cold start no deben competir por migrar el esquema).

**Comando exacto que el usuario ejecuta en su propia terminal** (desde `backend/`, con el venv activo, sin pegar la URL en ningún chat):

```powershell
.venv\Scripts\python -m alembic -x db_url="<cadena-de-conexion-pooler-de-produccion>" upgrade head
```

Reemplazando `<cadena-de-conexion-pooler-de-produccion>` por la URL real de la rama `main` de Neon con `-pooler`. El plan repite este comando en su tarea correspondiente, con el mismo marcador.

### 3.4 Koyeb — servicio web

- Tipo de despliegue: Dockerfile desde GitHub, auto-deploy en cada `git push` a `main` (ya decidido por el usuario).
- Variables de entorno a configurar en el dashboard de Koyeb (nombres únicamente, nunca valores en esta sesión):
  - `DATABASE_URL` — pooler de Neon, rama `main`.
  - `JWT_SECRET` — ≥32 caracteres, **distinto** del usado en tests.
  - `JWT_EXPIRE_MIN` — opcional, default 60 si se omite.
  - `PORT` — la inyecta Koyeb automáticamente; no se configura a mano.
  - Opcionales, solo para la creación del primer usuario Gerencia como *one-off job* (no en el servicio persistente): `GERENTE_NOMBRE`, `GERENTE_EMAIL`, `GERENTE_PASSWORD`.
- Healthcheck HTTP de Koyeb apuntando a `/api/v1/healthz` (ya existe desde 3.1, sin auth ni DB).

### 3.5 Cloudflare Pages — dos proyectos

| | Proyecto 1 (panel) | Proyecto 2 (PWA) |
|---|---|---|
| Root directory | `frontend` | `pwa` |
| Build command | `npm run build` | `npm run build` |
| Output directory | `dist` | `dist` |
| Variable de entorno | `VITE_API_URL` = URL pública de Koyeb | `VITE_API_URL` = URL pública de Koyeb |

- Archivo `_redirects` (`/* /index.html 200`) en `frontend/public/` y `pwa/public/` — sin esto, recargar cualquier ruta que no sea `/` da 404 en Cloudflare Pages (ambas son SPA con rutas en cliente).
- `sw.js`/`manifest.webmanifest` de la PWA: Cloudflare Pages sirve el `Content-Type` correcto por extensión sin configuración adicional.
- Conectar los dos proyectos en el dashboard de Cloudflare y configurar la variable de entorno es trabajo manual del usuario — el plan lo documenta como checklist explícito, no automatizable desde este entorno.

## 4. Manejo de errores

- **Dockerfile:** `asyncpg`/`argon2-cffi` publican wheels `manylinux` para CPython 3.12 en glibc (base de `python:3.12-slim`), así que `pip install` en el `builder` no debería requerir compilar nada. Si en la práctica Koyeb reporta un fallo de build por falta de una wheel, la tarea del plan que construye el Dockerfile agrega `build-essential` a la etapa `builder` (nunca a la final) como ajuste puntual — no se anticipa aquí para no instalar peso que probablemente no hace falta.
- **CORS:** un origen no listado nunca ve `Access-Control-Allow-Origin` — el navegador bloquea la respuesta del lado cliente; el backend igual procesa y responde (CORS no es una capa de autorización, es una instrucción para el navegador). La autorización real sigue siendo JWT + `require_role`, sin cambios.
- **Migración de producción:** si `alembic upgrade head` fallara a mitad de camino (poco probable en una migración `create_table` pura, sin `ALTER` destructivo), Postgres revierte la transacción de la migración fallida — Alembic ya ejecuta cada revisión dentro de una transacción por defecto.

## 5. Pruebas

- **CORS (pytest, automatizable):** una petición con `Origin: https://algo.pages.dev` a `/api/v1/healthz` debe reflejar ese origen en `Access-Control-Allow-Origin`; una con `Origin: https://evil.example` no debe reflejarlo; `http://localhost:5173` sí debe reflejarse.
- **Dockerfile (manual, ver sección 2):** build + run + `curl /healthz` — tarea del plan marcada explícitamente como ejecución del usuario, no del agente.
- **Cloudflare Pages (manual):** checklist de verificación post-deploy (la URL pública carga, `/alguna-ruta-inventada` no da 404 gracias a `_redirects`, la PWA se puede "instalar" desde el navegador móvil).
- **Suite existente:** correr `pytest` completo tras agregar `CORSMiddleware` para confirmar que no rompe ningún test de 3.1/3.2 (los tests actuales no envían `Origin`, así que no deberían verse afectados, pero se verifica).

## 6. Puntos que este spec resuelve explícitamente

- El Dockerfile no se prueba en este entorno por falta de Docker local — declarado, no escondido.
- La migración de producción la ejecuta el usuario con el comando exacto de la sección 3.3, nunca el agente ni con la URL pegada en el chat.
- CORS usa `allow_origin_regex` para `*.pages.dev` más una lista explícita de puertos de desarrollo, sin `allow_credentials`.
- Dos proyectos separados de Cloudflare Pages, cada uno con su propio *root directory* en el monorepo y su propio `_redirects`.
- Ningún workflow de GitHub Actions nuevo: Koyeb y Cloudflare Pages ya disparan su propio build+deploy vía integración nativa con git.
