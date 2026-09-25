# Desplegar frontend/ y pwa/ en Cloudflare Pages (dos proyectos)

## Proyecto 1 — Panel administrativo
1. Cloudflare dashboard → **Workers & Pages** → **Create** → **Pages** → **Connect to Git** → repo `Fildlab`.
2. **Root directory**: `frontend`.
3. **Build command**: `npm run build`.
4. **Build output directory**: `dist`.
5. Variables de entorno (Settings → Environment variables): `VITE_API_URL` = URL pública del servicio de Render (sin `/` final).
6. Branch de producción: `main`.

## Proyecto 2 — PWA de campo
Mismos pasos, con:
- **Root directory**: `pwa`.
- Mismo `VITE_API_URL`.

## Verificación post-deploy (Servicios en producción)
- **Panel Administrativo (Frontend Web):** `https://fildlab.pages.dev`
- **PWA de Campo para Técnicos:** `https://fildlab-pwa.pages.dev`
- **Backend API:** `https://fildlab-api.onrender.com` (Healthcheck: `/api/v1/healthz`, Swagger: `/docs`)

### Pruebas de funcionamiento:
- Ambas URLs cargan la pantalla de inicio y autenticación con certificados SSL/TLS 1.3 de Cloudflare.
- Navegar a una ruta interna directamente y recargar mantiene la app sin error 404 (reglas `_redirects` operativas).
- En navegadores móviles sobre la PWA (`https://fildlab-pwa.pages.dev`), aparece el aviso nativo "Instalar aplicación" (manifest e iconos oficiales validados).
- Conectividad API y CORS validados contra `https://fildlab-api.onrender.com`.
