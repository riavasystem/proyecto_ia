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

### Pendiente / próximos pasos sugeridos (al cierre del 2026-08-04, antes de la Fase 3)

- [x] ~~API pública con API keys, scopes y rate limit~~ — hecho, ver entrada siguiente.
- [ ] Endpoint `POST /api/v1/public/chat` y el motor de IA (intención → consulta → respuesta).
- [ ] Plugin Manager (`/plugins_runtime`) y primer plugin de ejemplo.
- [ ] Pantallas reales del panel administrativo — el frontend sigue siendo solo el dashboard placeholder; falta CRUD en UI para Servicios/Productos/Horarios/Promociones/Políticas/FAQ.
- [ ] Endpoint de logout / invalidación de refresh tokens (hoy no hay revocación, solo expiración).
- [ ] Considerar mover secretos de producción a un gestor (hoy el `.env` del servidor se armó a mano vía SSH).

---

## 2026-08-04 (cont.) — Fase 3: API pública con API keys, scopes y rate limit

### Qué se creó

**Modelo `ApiKey`** (`app/models/api_key.py`): key con prefijo visible (`sk_live_...`/`sk_test_...`) para identificarla en el panel sin exponer el secreto, hash SHA-256 (no Argon2 — necesitamos *buscar* la key por hash en cada request, no solo verificarla contra un candidato con salt), `environment`, `scopes` (string separado por comas, ver `API_KEY_SCOPES`), `rate_limit_per_minute`, `is_active`, `expires_at`, `last_used_at`.

**Endpoints admin `/api/v1/admin/api-keys`**: crear (la key en texto plano se devuelve **una sola vez**, en la respuesta del create), listar (sin el secreto), revocar (soft-delete vía `is_active=False`, para permitir rotación sin downtime con 2 keys activas — sección 10.2 del CLAUDE.md).

**Middleware de tenant extendido**: ahora resuelve tanto JWT (admin) como API keys (`sk_...`) desde el mismo header `Authorization: Bearer`. La resolución de API key vive en `app/services/api_keys.py` y corre con su propia sesión de DB (el middleware no tiene acceso a la sesión inyectada por `Depends`).

**Scopes y rate limit** (`app/api/deps.py::require_scope`, `app/api/rate_limit.py::enforce_rate_limit`): `require_scope("catalog:read")` solo aplica cuando la request viene autenticada con API key (las requests admin por JWT no están limitadas por scopes de API key). El rate limit es ventana fija de 60s en Redis (`tenant:{company_id}:ratelimit:{api_key_id}:{window}`), y **siempre** deja los headers `X-RateLimit-Limit/-Remaining/-Reset` en la respuesta (sección 10.7 del CLAUDE.md), no solo cuando se excede.

**Endpoints públicos de solo lectura**: `/api/v1/public/company`, `/services`, `/products`, `/promotions`, `/faq` — vía un factory genérico (`_public_list.py`, mismo patrón que el CRUD admin de la Fase 2). Todos requieren scope `catalog:read` y pasan por rate limit.

**Endpoint admin `/api/v1/admin/company`** (GET/PATCH): antes no había forma de leer/editar los datos de la propia empresa vía API — quedaba huérfano desde la Fase 2.

**Migración 0002**: tabla `api_keys`.

### Bugs encontrados y corregidos

1. **Aislamiento de tests roto para lo que pasa por middleware**: `resolve_api_key` usaba `async_session_factory` importado por nombre desde `app.db.session` — el `from X import Y` copia la referencia al momento del import, así que reasignar el atributo del módulo después (como hace el fixture de test para apuntar a la DB de prueba) no tenía efecto ahí. Se cambió a `import app.db.session as db_session` + `db_session.async_session_factory(...)` (acceso por atributo, evaluado en cada llamada) para que sí sea reemplazable desde `conftest.py`.
2. **mypy strict**: una variable `error` se usaba con dos subclases distintas de `DomainError` en las dos ramas del middleware sin anotación explícita — mypy infería el tipo de la primera asignación y fallaba en la segunda. Se agregó `error: DomainError`.
3. **500 en producción con cualquier API key válida** (el más importante, no lo agarró la suite de tests): `expires_at` y `last_used_at` en el modelo `ApiKey` no tenían `DateTime(timezone=True)` explícito — a diferencia de `TimestampMixin`, que sí lo tiene para `created_at`/`updated_at`. SQLAlchemy mapeaba la columna como *naive* (sin tz), pero el código escribe `datetime.now(UTC)` (con tz) → Postgres rechazaba el UPDATE. **SQLite no distingue esto**, así que los tests en memoria pasaban perfecto y el bug solo apareció al hacer smoke test contra Postgres real en producción. Lección: cualquier columna de fecha/hora nueva en un modelo necesita `DateTime(timezone=True)` explícito, no alcanza con el type hint `datetime`.

### Estado verificado en producción (2026-08-04)

Flujo completo probado contra `https://api-ia.riava.cl` (datos de prueba limpiados después): registro → crear servicio (admin/JWT) → crear API key con scope `catalog:read` → `GET /public/services` y `GET /public/company` con la key → 200, datos correctos, headers `X-RateLimit-*` presentes → key inválida → 401 `invalid_api_key`.

### Pendiente / próximos pasos sugeridos (al cierre de la Fase 3)

- [ ] Endpoint `POST /api/v1/public/chat` y el motor de IA (intención → consulta → respuesta) — sigue siendo el hueco más grande: hoy un tercero puede *leer* el catálogo pero no puede conversar con el asistente, que es el producto en sí.
- [ ] Webhooks salientes (sección 10.6) — no implementado en absoluto todavía.
- [ ] Endpoint `POST /api/v1/public/schedule` (horarios) — los otros 4 recursos públicos (company/services/products/promotions/faq) están, pero horarios (branches + business_hours + schedule_exceptions) quedó afuera de esta fase por tiempo.
- [ ] IP allowlist de API keys: el campo no existe todavía en el modelo (CLAUDE.md lo menciona como opcional) — no es bloqueante.
- [ ] Plugin Manager (`/plugins_runtime`) y primer plugin de ejemplo.
- [ ] Pantallas reales del panel administrativo (sigue siendo el dashboard placeholder).
- [ ] Endpoint de logout / invalidación de refresh tokens.
- [ ] Idempotency-Key en POSTs (sección 10.7) — hoy la API pública es solo lectura, así que no es urgente; sí lo será cuando exista `/public/chat`.
- [ ] Considerar mover secretos de producción a un gestor (hoy el `.env` del servidor se armó a mano vía SSH).
