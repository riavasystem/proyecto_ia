# Avances del proyecto

Registro cronológico de lo hecho. Léelo primero al retomar el proyecto — evita tener que re-explorar todo el repo o la infra desde cero.

## Convenciones de trabajo

- **No esperar `lint`/`typecheck`/`mypy`/`pytest` corriendo en local de forma indefinida.** La máquina de desarrollo (8GB RAM, varias sesiones de Claude Code/VSCode/Chrome abiertas a la vez) hace que estos comandos tarden minutos o se cuelguen. El pipeline de CI (`.github/workflows/ci.yml`) corre exactamente los mismos checks sin esa limitación. Flujo preferido: intentar el check en local con espera acotada; si tarda demasiado, **hacer commit y push igual** y dejar que CI sea el gate real, revisando el resultado vía `gh run view`/`gh run view --log-failed`. Si CI falla, corregir y volver a pushear — nunca forzar el merge con CI en rojo.
- Frontend en Vercel se despliega automáticamente vía la integración Git al hacer push a `main` — no depende del CLI local de Vercel ni de un workflow de GitHub Actions propio.

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

- [x] ~~Endpoint `POST /api/v1/public/chat` y el motor de IA~~ — hecho, ver entrada siguiente.
- [ ] Webhooks salientes (sección 10.6) — no implementado en absoluto todavía.
- [ ] Endpoint `POST /api/v1/public/schedule` (horarios) — los otros 4 recursos públicos (company/services/products/promotions/faq) están, pero horarios (branches + business_hours + schedule_exceptions) quedó afuera de esta fase por tiempo.
- [ ] IP allowlist de API keys: el campo no existe todavía en el modelo (CLAUDE.md lo menciona como opcional) — no es bloqueante.
- [ ] Plugin Manager (`/plugins_runtime`) y primer plugin de ejemplo.
- [ ] Pantallas reales del panel administrativo (sigue siendo el dashboard placeholder).
- [ ] Endpoint de logout / invalidación de refresh tokens.
- [ ] Idempotency-Key en POSTs (sección 10.7) — hoy la API pública es solo lectura, así que no es urgente; sí lo será cuando exista `/public/chat`.
- [ ] Considerar mover secretos de producción a un gestor (hoy el `.env` del servidor se armó a mano vía SSH).

---

## 2026-08-04 (cont.) — Fase 4: motor de IA heurístico + `POST /api/v1/public/chat`

### Decisión de arquitectura (consultada con el usuario)

El CLAUDE.md prohíbe RAG/embeddings/fine-tuning pero no prohíbe usar un LLM para redactar la respuesta a partir de datos ya consultados en Postgres (eso es tool-use, no RAG). Se ofrecieron dos caminos: LLM real (Claude API, requiere `ANTHROPIC_API_KEY` del usuario) o heurística sin LLM. **El usuario eligió arrancar con la heurística** — cero costo, cero dependencias externas, funciona hoy. Queda migrable a un LLM real después sin romper el contrato público, porque `/public/chat` no expone nada de la implementación interna (mismo request/response shape).

### Qué se creó

**`app/ai/`** (motor de IA, sección 7 del CLAUDE.md):
- `intent.py`: clasificación por palabras clave contra el mensaje (con fold de acentos vía `unicodedata`), categorías: greeting, schedule, services, products, promotions, policies, faq, unknown.
- `faq_matcher.py`: antes de clasificar por keywords, intenta matchear el mensaje contra las preguntas de FAQ reales del tenant por superposición de palabras significativas (con stopwords en español) — si hay match fuerte (≥50% de las palabras de la pregunta), gana sobre cualquier categoría genérica.
- `responder.py`: templates de respuesta en español que arman el texto a partir de los objetos reales (Service, Product, BusinessHour, Promotion, Policy) — nunca texto libre inventado, todo sale de lo que devuelve la query.
- `engine.py`: orquesta todo — `process_message(db, company_id, message) -> AIReply(intent, text)`.

**Modelos nuevos**: `Contact` (usuario final del tercero vía `external_id`, con `external_metadata` JSON — nunca se le pide que se registre en la plataforma, sección 10.5), `Conversation` (contact_id, channel, status, assigned_operator_id nullable para operadores humanos a futuro), `Message` (role, content, intent detectado).

**`POST /api/v1/public/chat`** (scope `chat:write`): resuelve/crea `Contact` por `(company_id, external_id)`, resuelve o crea `Conversation` (si mandan `conversation_id` la reutiliza), guarda el mensaje del usuario, corre el motor, guarda la respuesta, devuelve `{conversation_id, reply}`.

**`GET /api/v1/public/conversations/{id}`** (scope `conversations:read`) y **`POST .../close`** (scope `chat:write`).

**Admin `/api/v1/admin/conversations`** (list + detail, JWT) para que el panel pueda mostrar el historial — sección 9 del CLAUDE.md.

**Migración 0003**: `contacts`, `conversations`, `messages`.

### Bugs de mypy corregidos (no afectaban runtime, solo el gate de CI)

1. `dict | None` sin parámetros de tipo en 3 archivos (`Contact.external_metadata`, `ChatRequest.external_metadata`, un parámetro interno) → `dict[str, Any] | None`.
2. En `engine.py`, la variable `result` se reasignaba con el resultado de queries a modelos distintos (Service, luego Product, luego BusinessHour...) en ramas `if` separadas del mismo `async def`. mypy infiere el tipo de una variable local por su **primera** asignación en la función y no lo re-infiere en asignaciones posteriores con un tipo distinto, así que las ramas después de la primera tiraban error de tipo incompatible. Se corrigió usando un nombre de variable distinto por rama (`services_result`, `products_result`, etc.) — lección general: no reusar el mismo nombre de variable para resultados de queries de tipos distintos dentro de la misma función.

### Estado verificado en producción (2026-08-04)

Flujo completo contra `https://api-ia.riava.cl` (datos de prueba limpiados después): crear servicio real → crear API key con scopes `chat:write`+`conversations:read` → `POST /public/chat` con "Hola, buenas!" → responde saludando **con el nombre real de la empresa** → segundo mensaje "cuánto cuesta el corte?" en la misma conversación → responde citando **el servicio y precio reales** del catálogo → `GET /public/conversations/{id}` → historial completo con 4 mensajes (2 usuario + 2 asistente, con `intent` guardado en cada respuesta del asistente).

### Pendiente / próximos pasos sugeridos (al cierre de la Fase 4)

- [ ] `GET /api/v1/public/conversations` (listado) — no se implementó porque el CLAUDE.md exige paginación por cursor en listados públicos (sección 10.7) y no alcanzó el tiempo para hacerla bien; mejor no implementarla que implementarla violando el contrato.
- [ ] Endpoint público de horarios (`/public/schedule`) — sigue pendiente de la Fase 3.
- [ ] Webhooks salientes (sección 10.6) — sería el momento natural de emitir `message.received`/`message.replied` desde `/public/chat`.
- [ ] Migrar el motor de IA a un LLM real (Claude API) cuando el usuario decida — el contrato público no cambia, solo la implementación interna de `app/ai/engine.py`.
- [x] ~~Plugin Manager (`/plugins_runtime`) y primer plugin de ejemplo~~ — hecho, ver entrada siguiente.
- [ ] Pantallas reales del panel administrativo, incluyendo una vista de conversaciones (ya hay API: `/admin/conversations`).
- [ ] Endpoint de logout / invalidación de refresh tokens.
- [ ] Idempotency-Key en `POST /public/chat` (sección 10.7) — ahora que existe un POST público que crea recursos, esto empieza a ser relevante de verdad.
- [ ] Considerar mover secretos de producción a un gestor (hoy el `.env` del servidor se armó a mano vía SSH).

---

## 2026-08-04 (cont.) — Fase 5: Plugin Manager + plugin de ejemplo "agenda"

### Qué se creó

**`app/plugins_runtime/`** (runtime del Core, sección 8 del CLAUDE.md):
- `interface.py`: `PluginManifest` (Pydantic, valida `manifest.json`), `PluginContext` (dataclass — es **lo único** que un plugin puede tocar del Core: `company_id`, sesión de DB, cliente de Redis, `config`, logger, `user_id` opcional), `PluginResult` (`success`/`message`/`data`), `PluginInterface` (Protocol con `install`/`update`/`uninstall`/`configure`/`execute`/`check_permissions`).
- `registry.py`: descubre plugins recorriendo `PLUGINS_DIR` (nueva setting, default `../plugins` en dev local) buscando pares `manifest.json` + `plugin.py`. Un plugin con manifiesto inválido o que explota al importarse **se omite silenciosamente**, no tumba el arranque del Core — coherente con "un plugin que falla no puede tumbar el Core".
- `manager.py` (`PluginManager`): `install`/`uninstall`/`configure` propagan errores del plugin como `PluginExecutionError` (402→502, el admin necesita enterarse si algo falló). `execute()` es la pieza importante: corre con `asyncio.wait_for(..., timeout=plugin_execution_timeout_seconds)` (default 5s) y captura **cualquier** excepción, devolviendo siempre un `PluginResult` degradado en vez de propagar — nunca un 500.

**Modelo `InstalledPlugin`** (Core, no de plugin): qué plugins tiene instalados cada tenant, su `config` (JSON) y si está `is_enabled`. Administrar plugins es responsabilidad del Core (sección 4); el código del plugin en sí vive fuera, en `/plugins`.

**Endpoints**:
- Admin `/api/v1/admin/plugins`: `GET` (lista disponibles + estado de instalación por tenant), `POST /{name}/install`, `DELETE /{name}/uninstall`, `PATCH /{name}/configure`, `POST /{name}/enable`, `POST /{name}/disable`.
- Público `POST /api/v1/public/plugins/{name}/execute` (scope `plugins:execute`, sección 10.4): recibe `{action, payload}`, delega al `PluginManager`, devuelve `{success, message, data}`.

**Plugin de ejemplo "agenda"** (`/plugins/agenda/`, el mismo del manifiesto de ejemplo de la sección 8 del CLAUDE.md): reservas de citas simples. Tiene su propia tabla `plg_agenda_bookings` (prefijo `plg_<nombre>_` obligatorio) que el propio plugin crea en su `install()` vía SQL crudo — **nunca** toca tablas ni modelos del Core, ni los importa (solo importa `app.plugins_runtime.interface`, que es la API pública permitida, y `sqlalchemy` como dependencia externa normal). Acciones soportadas: `create_booking`, `list_bookings`. `check_permissions` solo permite esas dos acciones — cualquier otra se rechaza antes de llegar a `execute`.

### Cambio de infraestructura: Docker ahora buildea desde la raíz del repo

El backend original solo copiaba `backend/` a la imagen — pero `/plugins` es un directorio hermano, top-level, fuera de `backend/`. Sin este cambio, el Plugin Manager no tendría nada que descubrir en producción (el registry buscaría en un directorio que no existe dentro del contenedor).

- `backend/Dockerfile`: ahora asume que el build context es la **raíz del repo**, no `backend/` — todos los `COPY` cambiaron a rutas `backend/...` y se agregó `COPY plugins ./plugins` + `ENV PLUGINS_DIR=/app/plugins`.
- `.github/workflows/deploy-backend.yml`: `docker/build-push-action` pasó de `context: backend` a `context: .` + `file: backend/Dockerfile`. El trigger `paths:` ahora también incluye `plugins/**` (un cambio solo en un plugin ahora sí redeploya el backend).
- `.dockerignore` se movió de `backend/.dockerignore` a la raíz (Docker solo respeta el que está en la raíz del build context).
- `docker-compose.yml` (dev local): mismo cambio de contexto, más un volumen nuevo `./plugins:/app/plugins` para hot-reload de plugins en desarrollo.

**Verificado en el servidor**: `docker exec proyecto_ia-backend-1 ls /app/plugins/agenda` muestra `manifest.json` y `plugin.py` — la imagen sí los tiene.

### Nota sobre la máquina de desarrollo (siguió mejorando)

Con menos apps abiertas, `mypy` corrió local sin problema esta vez (antes tiraba `INTERNAL ERROR` o tardaba +10 min). `pytest` completo siguió lento (varios minutos), así que la confirmación final se hizo en CI como en las fases anteriores — pero cada vez hay menos fricción.

### Estado verificado en producción (2026-08-04)

Flujo completo contra `https://api-ia.riava.cl` (datos de prueba limpiados después): `GET /admin/plugins` muestra "agenda" disponible y no instalado → `POST /admin/plugins/agenda/install` → 201, crea `plg_agenda_bookings` → API key con scope `plugins:execute` → `POST /public/plugins/agenda/execute` con `action: create_booking` → reserva creada → `action: list_bookings` → la trae de vuelta.

### Pendiente / próximos pasos sugeridos (al cierre de la Fase 5)

- [ ] Las migraciones de plugins no pasan por Alembic todavía — el plugin crea su tabla a mano en `install()` (`CREATE TABLE IF NOT EXISTS`). Funciona para el MVP pero no soporta migraciones de esquema versionadas ni rollback de las tablas del plugin. La sección 8 del CLAUDE.md pide "migraciones propias, dentro del plugin" — falta el mecanismo que las aplique de forma versionada.
- [ ] El motor de IA (`app/ai/engine.py`) todavía no invoca plugins automáticamente — hoy `/public/chat` y `/public/plugins/{name}/execute` son dos caminos separados. Sección 7: "determinar si debe ejecutarse un plugin" sigue sin resolver del lado del motor de IA (el tercero tiene que saber que existe el plugin y llamarlo él mismo).
- [ ] Sistema de eventos/hooks declarado en el manifiesto (`hooks: ["message.received", "conversation.closed"]`) no está conectado a nada todavía — el manifiesto los declara pero no hay un event bus que los dispare cuando ocurren esos eventos reales.
- [ ] Credenciales de plugins cifradas por tenant (sección 8) — no aplica todavía porque "agenda" no usa credenciales externas, pero el mecanismo genérico no existe.
- [ ] Endpoint público de horarios (`/public/schedule`), listado de conversaciones con cursor, webhooks salientes — siguen pendientes de fases anteriores.
- [ ] Pantallas reales del panel administrativo (incluyendo una para plugins: instalar/configurar/ver desde la UI).
- [ ] Endpoint de logout / invalidación de refresh tokens.
- [ ] Considerar mover secretos de producción a un gestor (hoy el `.env` del servidor se armó a mano vía SSH).

---

## 2026-08-04 (cont.) — Fase 6: pantallas del panel administrativo

### Qué se creó

Primer set de pantallas reales sobre la API que ya existía (hasta ahora el frontend era solo el placeholder con el health check). Todo consume exclusivamente `/api/v1/admin/...` con JWT — cero lógica de negocio en el frontend (sección 9 del CLAUDE.md).

- **Auth**: `lib/auth-context.tsx` (`AuthProvider`/`useAuth`), páginas `/login` y `/register`. El token vive en `localStorage` y se lee vía `useSyncExternalStore` (no un `useEffect` + `setState`) para evitar mismatch de hidratación entre servidor y cliente.
- **Layout protegido** `app/(panel)/layout.tsx`: navegación lateral a las 9 secciones, redirige a `/login` si no hay sesión.
- **`lib/crud-page.tsx`**: componente CRUD genérico (tabla + formulario) parametrizado por tipo, reutilizado en Servicios, Productos, Promociones, Políticas y FAQ — mismo patrón que `_crud.py` del backend, pero en el frontend.
- **Empresa**: pantalla de edición de registro único (get/patch).
- **API Keys**: alta con selección de scopes, aviso de que el valor completo solo se muestra una vez, listado con revocación.
- **Plugins**: lista disponibles + instalados, instalar/desinstalar/habilitar/deshabilitar.
- **Conversaciones**: lista + vista de historial de mensajes con burbujas por rol.
- **Dashboard**: contadores simples (servicios, productos, conversaciones, plugins instalados).

### Bug de lint no trivial: `react-hooks/set-state-in-effect`

`eslint-config-next` trae ahora el linter del compilador de React, que marca como error cualquier `setState` alcanzable desde un `useEffect` — incluso detrás de un `await`, incluso si está condicionado por un ref de "montado". Esto rompe el patrón clásico de fetch-on-mount (`useEffect(() => { void load() }, [])`) que usan casi todas las pantallas nuevas.

Se probaron dos soluciones antes de la correcta:
1. Quitar el `setIsLoading(true)` redundante del inicio de `load()` — no alcanzó, la regla sigue seguimiento el resto de la cadena.
2. Guardar los `setState` con un ref de "montado" (`useIsMounted`) — tampoco satisfizo la regla, y además **rompió la memoización del React Compiler** en `crud-page.tsx` (acceder a `ref.current` dentro de las dependencias de un `useCallback` invalida su análisis estático — error separado: "Compilation Skipped: Existing memoization could not be preserved").

Solución final: revertir a los efectos simples y usar `// eslint-disable-next-line react-hooks/set-state-in-effect` puntual, con comentario explicando que es un falso positivo conocido para este patrón (documentado también como lección en este archivo, no solo en el código, por si se repite en pantallas futuras). `auth-context.tsx` sí tiene una solución de fondo real: `useSyncExternalStore` en vez de efecto, porque ahí el problema de hidratación es genuino y no un falso positivo.

### Convención de trabajo agregada

Durante esta fase la máquina volvió a ser lenta para `npm run lint`/`typecheck` en local (varios minutos, a veces sin terminar). Se documentó al inicio de este archivo (sección "Convenciones de trabajo") y como memoria persistente: no esperar esos checks localmente de forma indefinida, pushear y dejar que CI sea el gate.

### Estado verificado en producción (2026-08-04)

- Las 10 rutas del panel (`/login`, `/register`, `/dashboard`, `/empresa`, `/servicios`, `/productos`, `/promociones`, `/politicas`, `/faq`, `/plugins`, `/api-keys`, `/conversaciones`) responden 200 en `https://proyecto-ia-wheat.vercel.app`, desplegadas automáticamente por la integración Git de Vercel tras el push a `main`.
- Smoke test contra `https://api-ia.riava.cl` de los endpoints que consume el panel (registro → `GET/PATCH company` → crear servicio → `GET plugins`), todos con el mismo token JWT que usaría la sesión del navegador. Datos de prueba limpiados después.
- CI (`ci.yml`) verde en el commit final (`7df55d4`) tras tres iteraciones de fix para el lint del compilador de React.

### Pendiente / próximos pasos sugeridos (al cierre de la Fase 6)

- [ ] Pantallas de Branches/Horarios (`BusinessHour`/`ScheduleException`) — la API existe (`/admin/branches`, `/admin/schedule`) pero no se armó UI porque requiere selects de sucursal, más complejo que el CRUD genérico plano usado para el resto.
- [ ] Pantalla de Usuarios/permisos del panel (RBAC) — no hay endpoint admin de gestión de usuarios todavía, solo el usuario creado en el registro inicial.
- [ ] Pantalla de Canales (Web, WhatsApp, Instagram, Messenger, Telegram) — no hay modelo/endpoint de canales todavía en el Core.
- [ ] Pantalla de Configuración (idioma, zona horaria, IA, seguridad, tokens).
- [ ] El motor de IA (`app/ai/engine.py`) sigue sin invocar plugins automáticamente — pendiente de Fase 5.
- [ ] Migraciones de plugins versionadas, hooks/eventos, endpoint público de horarios, webhooks salientes, listado de conversaciones con cursor — todo pendiente de fases anteriores.
- [ ] Logout / invalidación de refresh tokens (el botón "Cerrar sesión" del panel solo borra el token local, no lo invalida en el servidor).
