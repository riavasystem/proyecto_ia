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

### Pendiente / próximos pasos sugeridos (al cierre del 2026-08-03)

- [ ] Modelos y endpoints de negocio: Servicio, Producto, Horario, Promoción, Política, FAQ (con migraciones Alembic y CRUD completo, sección 6 del CLAUDE.md).
- [ ] Motor de IA: intención → consulta de datos → construcción de respuesta (sección 7).
- [ ] Plugin Manager (`/plugins_runtime`) y primer plugin de ejemplo.
- [ ] Autenticación real de usuarios del panel (endpoints de login/refresh — hoy solo existe `create_access_token`/`create_refresh_token` en `core/security.py`, sin rutas expuestas).
- [ ] Pantallas reales del panel administrativo (hoy solo hay un dashboard placeholder).
- [ ] API pública `/api/v1/public/...` completa (hoy solo existe el health check).
- [ ] Considerar mover secretos de producción a un gestor (hoy el `.env` del servidor se armó a mano vía SSH).

---

## 2026-08-04 — Fase 2: entidades de negocio, CRUD genérico, auth real

### Qué se creó

**Modelos de negocio** (sección 6 del CLAUDE.md), todos con `company_id` obligatorio: `Service`, `Product`, `Branch`, `BusinessHour`, `ScheduleException`, `Promotion`, `Policy`, `FAQ`. `Horario` se modeló como `Branch` (sucursal) + `BusinessHour` (horario semanal recurrente, `day_of_week` 0-6) + `ScheduleException` (feriados/cambios puntuales por fecha).

**CRUD genérico** (`app/api/v1/routes/_crud.py`): en vez de escribir 6 routers CRUD casi idénticos, hay un factory `build_crud_router(model, create_schema, update_schema, read_schema, prefix, tags)` que genera list/create/get/update/delete, y **siempre** filtra por `company_id` (vía la dependency `CurrentCompanyId` en `app/api/deps.py`, que lee `request.state.company_id` seteado por el middleware de tenant). Cada entidad (`services.py`, `products.py`, etc.) es un archivo de ~10 líneas que solo llama al factory. mypy strict no puede verificar los tipos paramétricos ahí (son dinámicos en runtime) — tiene `# type: ignore` puntuales, documentado en el docstring del módulo.

**Auth real**: antes solo existían las funciones de firma JWT sin rutas. Ahora hay `POST /api/v1/admin/auth/register` (crea Company + primer User admin), `/login`, `/refresh`. El email de usuario es **único a nivel global** (no por tenant) porque el login necesita resolver el `company_id` a partir del email antes de tener contexto de tenant — está comentado en `models/user.py`.

**Migración Alembic inicial** (`0001_13eb523abbcc_initial_schema.py`): escrita a mano (no autogenerada) porque la máquina de desarrollo estaba con muy poca RAM libre ese día y correr Postgres local vía Docker hacía todo insoportablemente lento. Crea las 10 tablas (companies, users, y las 8 de negocio). **Importante**: no existía ninguna migración antes de hoy — la base de datos de producción estuvo sin ninguna tabla real desde el deploy inicial (el health check nunca lo hubiera detectado porque solo hace `SELECT 1`).

**Tests**: `tests/conftest.py` con fixture `client` (SQLite en memoria + `httpx.AsyncClient` sobre la app real vía ASGI transport, con `app.dependency_overrides` para inyectar la sesión de test). `tests/test_tenant_isolation.py` verifica que una empresa no puede leer/editar/borrar recursos de otra (ni por listado ni por id directo → 404, no 403, para no filtrar existencia).

### Bug encontrado y corregido

**Tipo `UUID` de Postgres impedía testear con SQLite**: `db/base.py` y `models/schedule.py` usaban `sqlalchemy.dialects.postgresql.UUID`, que es específico de ese dialecto y no compila contra SQLite. Se cambió a `sqlalchemy.Uuid` (el tipo genérico de SQLAlchemy 2.0), que compila a UUID nativo en Postgres y a `CHAR(32)` en SQLite — mismo comportamiento en producción, pero ahora testeable sin Docker. La migración Alembic también se actualizó a `sa.Uuid` para que coincida.

**Middleware de tenant no formateaba bien los 401**: `TenantContextMiddleware` hacía `raise UnauthorizedError(...)` cuando el JWT era inválido/expiraba. Como los middlewares agregados con `app.add_middleware` corren **por fuera** del `ExceptionMiddleware` de Starlette (que es donde FastAPI engancha los `exception_handler` registrados con `add_exception_handler`), esa excepción nunca llegaba a `domain_error_handler` — se hubiera visto como un 500 crudo en vez de un 401 con el formato `{"error": {...}}`. Se corrigió llamando a `domain_error_handler` directamente y retornando su response, en vez de `raise`. Esto no se había detectado antes porque hasta hoy nada mandaba tokens Bearer reales.

### Estado verificado en producción (2026-08-04)

Se probó el flujo completo contra `https://api-ia.riava.cl` (y se limpiaron los datos de prueba después):
- `POST /api/v1/admin/auth/register` → 201, devuelve `access_token`/`refresh_token`.
- `POST /api/v1/admin/services` con el token → 201, crea el servicio con el `company_id` correcto.
- `GET /api/v1/admin/services` con el token → 200, lista solo lo de esa empresa.
- `GET /api/v1/admin/services` sin token → 401 con el formato de error correcto.
- El deploy corrió `alembic upgrade head` en el servidor y creó las 10 tablas por primera vez.

### Nota sobre la máquina de desarrollo

Ese día la Mac de desarrollo tenía varias sesiones de Claude Code + VSCode + Chrome corriendo en paralelo con 8GB de RAM total — cualquier comando local (`pip install`, `mypy`, `pytest`, hasta `git add`) tardaba entre 2 y 20 minutos, y `mypy` llegó a tirar un `INTERNAL ERROR` por presión de memoria. La verificación real de mypy/pytest terminó haciéndose en GitHub Actions (que no tiene esa limitación), no localmente. Si esto se repite: no pelear con la máquina local, hacer `ruff check` (liviano, siempre anduvo rápido) y dejar que CI valide el resto.

### Pendiente / próximos pasos sugeridos (al cierre del 2026-08-04)

- [ ] API pública `/api/v1/public/...` con API keys (`sk_live_`/`sk_test_`), scopes y rate limit (sección 10.2 del CLAUDE.md) — hoy los endpoints de negocio solo existen del lado admin (JWT), no hay forma de que un proyecto externo los consuma todavía.
- [ ] Endpoint `POST /api/v1/public/chat` y el motor de IA (intención → consulta → respuesta).
- [ ] Plugin Manager (`/plugins_runtime`) y primer plugin de ejemplo.
- [ ] Pantallas reales del panel administrativo — el frontend sigue siendo solo el dashboard placeholder; falta CRUD en UI para Servicios/Productos/Horarios/Promociones/Políticas/FAQ.
- [ ] Endpoint de logout / invalidación de refresh tokens (hoy no hay revocación, solo expiración).
- [ ] Considerar mover secretos de producción a un gestor (hoy el `.env` del servidor se armó a mano vía SSH).
