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
