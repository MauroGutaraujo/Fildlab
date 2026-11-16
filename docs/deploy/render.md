# Desplegar el backend en Render

Reemplaza a Koyeb (pausó el alta de cuentas nuevas/gratuitas por su reestructuración con
Mistral AI). El `Dockerfile` no necesita ningún cambio: ya usa `${PORT:-8000}` en el `CMD`,
y Render inyecta `$PORT` en runtime igual que Koyeb.

## Prerrequisito
La Tarea 2 (migración de Neon producción) debe estar completa antes de este paso.

## 1. Crear el servicio
1. En el dashboard de Render: **New** → **Web Service** → **Build and deploy from a Git repository** → conectar el repo `Fildlab`.
2. **Root Directory**: `backend`.
3. **Runtime**: **Docker** (Render detecta el `Dockerfile` en la raíz del Root Directory).
4. **Dockerfile Path**: `backend/Dockerfile` (o `Dockerfile` si el Root Directory ya es `backend`).
5. **Branch**: `main`. **Auto-Deploy**: `Yes` (cada `git push` a `main` redespliega).
6. **Instance Type**: **Free** (512 MB RAM, 0.1 CPU — mismo límite que ya asumía el Dockerfile para Koyeb).

## 2. Variables de entorno (Render → Environment)

| Variable | Valor |
|---|---|
| `DATABASE_URL` | Cadena de conexión del pooler de Neon, rama `main` (producción) |
| `JWT_SECRET` | ≥32 caracteres, distinto del usado en tests — generar con `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `JWT_EXPIRE_MIN` | Opcional. Si se omite, default 60. |

`PORT` no se configura manualmente: Render la inyecta automáticamente (típicamente `10000`) y el `CMD` del Dockerfile ya la respeta vía `${PORT:-8000}`.

## 3. Healthcheck
Render → Settings → **Health Check Path**: `/api/v1/healthz`. Este endpoint no requiere autenticación ni toca la base de datos (mitiga cold starts, RNF-01) — en el free tier de Render es todavía más importante que en Koyeb, porque el servicio **se apaga tras 15 minutos de inactividad** y el siguiente request tarda ~30-50s en despertarlo (cold start más largo que el de un contenedor "efímero" tradicional). Un ping externo periódico a `/api/v1/healthz` (p. ej. un cron externo gratuito, o el propio uptime monitor de Render) mantiene el servicio despierto en horario comercial.

## 4. Crear el primer usuario Gerencia (una sola vez)
El free tier de Render no ofrece *one-off jobs* gratuitos equivalentes a los de Koyeb. La forma más simple y seteo-libre de crear el primer usuario Gerencia es correr el script **localmente**, apuntando a la base de datos de producción — el mismo patrón ya usado para la migración de Alembic (Tarea 2), sin depender de ninguna función de la plataforma:

```powershell
cd backend
$env:DATABASE_URL = "<cadena-de-conexion-pooler-de-produccion>"
$env:JWT_SECRET = "<el-mismo-JWT_SECRET-configurado-en-Render>"
$env:GERENTE_NOMBRE = "..."
$env:GERENTE_EMAIL = "..."
$env:GERENTE_PASSWORD = "..."
.venv\Scripts\python -m app.scripts.crear_gerente
```

(Si tu plan de Render sí incluye acceso a **Shell** para el servicio, correr el mismo comando `python -m app.scripts.crear_gerente` ahí es una alternativa equivalente, con las variables ya cargadas desde el Environment del servicio.)

### Cambiar la contraseña de un usuario existente
Ninguna contraseña se guarda en el repositorio. Para cambiarla, con las mismas variables `DATABASE_URL` y `JWT_SECRET` del paso anterior (o desde la **Shell** de Render):

```powershell
cd backend
.venv\Scripts\python -m app.scripts.cambiar_password gerencia@fildlab.pe
.venv\Scripts\python -m app.scripts.cambiar_password tecnico@fildlab.pe
```

El script pide la nueva contraseña dos veces sin mostrarla (mínimo 12 caracteres) y solo guarda su hash Argon2.

## 5. Verificación post-deploy (Servicio en producción: `https://fildlab-api.onrender.com`)
- `curl https://fildlab-api.onrender.com/api/v1/healthz` → `{"status":"ok"}`.
- `curl -X POST https://fildlab-api.onrender.com/api/v1/auth/login -H "Content-Type: application/json" -d "{\"email\":\"...\",\"password\":\"...\"}"` con el usuario Gerencia recién creado → debe devolver un `access_token`.
- Documentación Swagger/OpenAPI interactiva: `https://fildlab-api.onrender.com/docs`.
- `VITE_API_URL` en los dos proyectos de Cloudflare Pages (ver `docs/deploy/cloudflare-pages.md`) apunta a `https://fildlab-api.onrender.com`.
