# Avances del proyecto

Registro cronológico de lo hecho. Léelo primero al retomar el proyecto — evita tener que re-explorar todo el repo o la infra desde cero.

---

## 2026-08-03 — Bootstrap inicial: repo, backend, frontend, CI/CD, deploy a producción

### Qué se creó

**Backend** (`/backend`) — FastAPI async + SQLAlchemy 2.x + Alembic + PostgreSQL + Redis.
- Health check (`/api/v1/public/health`), config vía `pydantic-settings`, logging estructurado (`structlog`), JWT (access+refresh) con Argon2id, middleware de tenant (`company_id` desde JWT, nunca del body) y de `X-Request-ID`.
- Modelos iniciales: `Company`, `User` (con mixins `UUIDPrimaryKeyMixin`, `TimestampMixin`, `TenantMixin`).
- Solo hay estructura y health check — **no hay lógica de negocio real todavía** (sin Servicios, Productos, Horarios, etc.).
- Calidad verificada: `ruff`, `mypy --strict`, `pytest` pasando.

**Frontend** (`/frontend`) — Next.js App Router + TypeScript strict + Tailwind.
- Un solo dashboard placeholder en `app/page.tsx` que hace `fetch` al health check del backend (`lib/api.ts`, usa `NEXT_PUBLIC_API_URL`).
- Sin pantallas reales de negocio todavía (Servicios, Productos, etc. del punto 9 del CLAUDE.md).

**Infra / CI-CD**
- `docker-compose.yml` (dev local) y `docker/docker-compose.prod.yml` (servidor).
- GitHub Actions: `.github/workflows/ci.yml` (ruff+mypy+pytest backend, lint+typecheck+build frontend) y `.github/workflows/deploy-backend.yml` (build imagen → push a GHCR → SSH al servidor → `docker compose up` → `alembic upgrade head`).
- **El frontend NO se deploya vía GitHub Actions** — se decidió usar solo la integración nativa Git de Vercel (auto-deploy en cada push a `main`), porque tener las dos a la vez generaba deploys duplicados. Si en algún momento se necesita más control (logs centralizados, gates de tests antes de deploy), se puede reintroducir `deploy-frontend.yml` (existe en el historial de git, commit `a815282` lo eliminó).

### Estado de producción (deploy verificado end-to-end)

| Componente | URL / ubicación | Detalle |
|---|---|---|
| Backend | https://api-ia.riava.cl | Docker en `root@49.12.66.17:/opt/apps/proyecto_ia`, puerto interno **8010** (host) → 8000 (contenedor) |
| Frontend | https://proyecto-ia-wheat.vercel.app | Vercel, team **ClientesRiava**, proyecto `proyecto-ia` (`prj_fIesRVk9G2jZFjTUg3a32aCfDutr`) |
| Repo | git@github.com:riavasystem/proyecto_ia.git | rama `main` |

**Servidor** (`49.12.66.17`, Ubuntu 24.04):
- Es un servidor **compartido** con otras apps: `clientefiel` (puerto 8000), `controlcost` (8001), `finopslatam`, `studiodesk` (8002). **Antes de asignar un puerto nuevo, correr `ss -tlnp` en el servidor** — no asumir que 8000/8001/8002 están libres.
- `docker-compose.prod.yml` vive en `/opt/apps/proyecto_ia/docker-compose.prod.yml`, `.env` real (con secretos) vive en `/opt/apps/proyecto_ia/.env` (no está en el repo, generado a mano con `openssl rand -hex 32` para `JWT_SECRET` y `openssl rand -hex 20` para `POSTGRES_PASSWORD`).
- Nginx: config en `/etc/nginx/sites-available/proyecto_ia.conf` → proxy a `127.0.0.1:8010`. TLS con Certbot (Let's Encrypt), auto-renovación configurada, expira 2026-11-01.
- Acceso SSH: key dedicada de CI en `~/.ssh/proyecto_ia_deploy/ci_deploy_key` (local, en esta Mac) instalada en `authorized_keys` del servidor. GitHub Actions usa el secret `SSH_PRIVATE_KEY` con esta misma key.

**GitHub** (`riavasystem/proyecto_ia`):
- Cuenta dueña: `riavasystem` (NO usar `finopslatam-sudo`, esa cuenta solo tiene lectura y el usuario pidió explícitamente no usarla).
- Push/git: configurado un alias SSH dedicado en `~/.ssh/config` → `Host github-riavasystem` con `IdentityFile ~/.ssh/id_ed25519_riavasystem`. El remote del repo local usa `git@github-riavasystem:riavasystem/proyecto_ia.git`.
- Secrets de Actions ya configurados (por el usuario, vía dashboard web — los tokens que probamos por API/PAT fallaban de forma persistente para esta cuenta sin causa clara, incluso con scopes correctos; el push SSH y la web sí funcionan): `SSH_HOST`, `SSH_USER`, `SSH_PRIVATE_KEY`, `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`.

**Vercel**:
- Cuenta: `riava.system@gmail.com` (usuario `riavasystem-9641`), team **ClientesRiava** (`team_7JgFlEGMKSscR8hR5Tdam2G7`).
- Proyecto correcto: `proyecto-ia` (`prj_fIesRVk9G2jZFjTUg3a32aCfDutr`), `rootDirectory=frontend`, `framework=nextjs`.
- Se eliminaron 2 proyectos duplicados que se habían creado por error: `proyecto_ia` y `proyecto-ia-nuevo`.
- Env var `NEXT_PUBLIC_API_URL=https://api-ia.riava.cl` seteada en Production.

**DNS** (Cloudflare, zona `riava.cl`):
- Registro `api-ia.riava.cl` → `A` → `49.12.66.17`, **Proxy status: DNS only** (nube gris — tiene que quedar así para que Certbot pueda validar; si se pasa a Proxied, el certificado deja de poder renovarse vía challenge HTTP).

### Bugs encontrados y corregidos (para no repetirlos)

1. **YAML inválido en `ci.yml`**: `DATABASE_URL: sqlite+aiosqlite:///:memory:` sin comillas — el `:` final rompía el parser de GitHub Actions (fallaba sin generar jobs, con el run mostrando el path del archivo como nombre en vez del `name:` declarado — esa es la señal de que el workflow no se pudo parsear). Se corrigió citando el valor.
2. **`CORS_ORIGINS` mal seteado**: al principio apuntaba al dominio del propio backend (`api-ia.riava.cl`) en vez del dominio del frontend. Corregido a los dominios de Vercel.
3. **Puerto ocupado**: el compose de producción mapeaba el backend a `127.0.0.1:8000`, pero ese puerto (y luego 8001, y 8002) ya estaban tomados por otras apps del mismo servidor. Terminó en **8010**.
4. **Typo de DNS**: el registro se creó como `app-ia.riava.cl` en vez de `api-ia.riava.cl` — causó ~30 min de debugging porque el registro "existía" en el dashboard de Cloudflare pero el nombre no coincidía con el que usábamos. Si un dominio no resuelve pero "aparece" en el dashboard, comparar el `Name` letra por letra.

### Pendiente / próximos pasos sugeridos

- [ ] Modelos y endpoints de negocio: Servicio, Producto, Horario, Promoción, Política, FAQ (con migraciones Alembic y CRUD completo, sección 6 del CLAUDE.md).
- [ ] Motor de IA: intención → consulta de datos → construcción de respuesta (sección 7).
- [ ] Plugin Manager (`/plugins_runtime`) y primer plugin de ejemplo.
- [ ] Autenticación real de usuarios del panel (endpoints de login/refresh — hoy solo existe `create_access_token`/`create_refresh_token` en `core/security.py`, sin rutas expuestas).
- [ ] Pantallas reales del panel administrativo (hoy solo hay un dashboard placeholder).
- [ ] API pública `/api/v1/public/...` completa (hoy solo existe el health check).
- [ ] Considerar mover secretos de producción a un gestor (hoy el `.env` del servidor se armó a mano vía SSH).
