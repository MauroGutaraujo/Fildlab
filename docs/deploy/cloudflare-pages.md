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

## Verificación post-deploy (ambos proyectos)
- La URL `*.pages.dev` asignada carga la pantalla de login.
- Navegar a una ruta que no exista en el historial del navegador (pegar la URL de una pantalla interna directamente) y recargar: debe seguir mostrando la app, no un 404 de Cloudflare — confirma que `_redirects` se aplicó.
- Solo para el proyecto de la PWA: en un navegador móvil (o Chrome DevTools → Application → Manifest), confirmar que aparece la opción "Agregar a pantalla de inicio" / "Instalar" — confirma que `manifest.webmanifest` y `sw.js` se sirvieron correctamente.
- Iniciar sesión contra el backend real de Render desde ambas URLs de Cloudflare Pages — confirma que CORS (Tarea 0) permite el origen `*.pages.dev` real, no solo el patrón en el test.
