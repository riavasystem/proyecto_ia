# CLAUDE.md

Guía operativa para trabajar en este repositorio. Léela completa antes de escribir código.


## 1. Qué es este proyecto

Plataforma SaaS **multi-tenant** que permite a cualquier empresa crear un **asistente digital** que atiende clientes por múltiples canales (Web, WhatsApp, Instagram, Messenger, API pública) usando **exclusivamente la información estructurada que la empresa carga en el sistema**, y ampliable mediante **plugins independientes**.

Es un producto **independiente**. No está ligado a FinopsLatam, ClienteFiel, Riava ni a ningún otro sistema. Se integra con cualquier producto actual o futuro vía API REST.

### Esta plataforma es un servicio consumible por otros proyectos

Este proyecto **no es una app final, es un servicio**. Otros proyectos —presentes y futuros, propios o de terceros— lo consumirán desde afuera como si fuera un proveedor externo (tipo Stripe o Twilio): se registran, obtienen una API key, llaman la API y reciben webhooks.

Consecuencia práctica en cada decisión de diseño:

- Todo lo que hace la plataforma debe ser accesible desde fuera, sin acceso a la base de datos ni a código interno.
- Integrar un proyecto nuevo debe tomar minutos, no días: una API key, una llamada HTTP o un `<script>`, y funciona.
- La API pública es un **contrato**: se versiona, se documenta y no se rompe. El panel administrativo es solo un cliente más de esa API.
- Si al construir algo no puedes explicar cómo lo consumiría un proyecto externo, el diseño está incompleto.

Ver **sección 10** para el detalle de integración.

### Regla fundamental

> **El Core es pequeño, estable y genérico. Toda lógica de negocio vive en plugins.**

Si una funcionalidad describe *qué hace un negocio* (agendar, cotizar, cobrar, CRM), es un **plugin**.
Si describe *cómo funciona la plataforma* (auth, tenants, conversaciones, routing de intención), es **Core**.

### Regla de conocimiento del asistente

La IA **no** aprende de documentos, PDFs, archivos ni embeddings.
La IA responde **solo** con datos estructurados leídos desde PostgreSQL (servicios, productos, horarios, promociones, políticas, FAQ) y con resultados devueltos por plugins.

Prohibido introducir: ingesta de PDFs, vector stores, RAG por embeddings, fine-tuning por tenant.

---

## 2. Stack

**Backend**

- Python 3.13
- FastAPI (async)
- SQLAlchemy 2.x (estilo declarativo, async engine)
- Pydantic v2 (schemas + settings)
- Alembic (migraciones)
- PostgreSQL 16
- Redis (caché, sesiones, rate limit, colas ligeras)

**Frontend**

- Next.js (App Router)
- React + TypeScript (strict)
- Tailwind CSS
- Solo panel administrativo. **No** es donde conversan los clientes finales.

**Infraestructura**

- Docker / docker-compose
- Nginx (reverse proxy, TLS)
- GitHub (repo + CI)
- Vercel (frontend)
- Servidor Linux/Cloud (backend)

**Seguridad**

- HTTPS obligatorio
- JWT + Refresh Tokens
- Argon2id para contraseñas
- RBAC (roles + permisos granulares)
- Rate limiting por tenant y por IP
- Auditoría de acciones
- Logs estructurados (JSON)
- Aislamiento total por empresa (multi-tenant)

---

## 3. Estructura del repositorio (monorepo)

```
/backend
  /app
    /core            # config, seguridad, deps, excepciones, logging
    /db              # engine, session, base, mixins
    /models          # SQLAlchemy (solo tablas del Core)
    /schemas         # Pydantic
    /api
      /v1
        /routes      # endpoints del Core
    /services        # servicios del Core (sin lógica de negocio de cliente)
    /ai              # motor IA: intención, contexto, construcción de respuesta
    /channels        # adaptadores de canal -> mensaje normalizado
    /plugins_runtime # plugin manager, registry, loader, hooks, eventos
    /middleware      # tenant, auth, rate limit, request-id
  /migrations        # Alembic
  /tests
/plugins
  /<plugin_name>
    plugin.py        # clase que implementa PluginInterface
    manifest.json
    /models
    /schemas
    /services
    /api
    /migrations
    /ui              # definición de pantallas para el panel
    /tests
/frontend
  /src/app           # App Router
  /src/components
  /src/lib           # api client, auth, tipos generados
  /src/features      # dashboard, empresa, servicios, productos, ...
/widget              # snippet embebible <script> para webs de terceros
/sdk
  /python            # cliente oficial Python
  /javascript        # cliente oficial JS/TS (Node + browser)
/docker
/docs
  openapi.json       # contrato público, generado
  /integration       # guías de integración para proyectos externos
```

---

## 4. Responsabilidades del Core

El Core **solo** hace esto:

1. Administrar usuarios
2. Administrar empresas (tenants)
3. Administrar conversaciones y mensajes
4. Comprender la intención del usuario
5. Consultar la información del negocio (datos estructurados)
6. Determinar si debe ejecutarse un plugin
7. Ejecutar el plugin correspondiente
8. Construir la respuesta con la información obtenida
9. Registrar todas las acciones (auditoría + logs)

**El Core nunca contiene lógica de negocio.** Si estás por escribir "si el rubro es peluquería..." en el Core, detente: eso es un plugin.

### Flujo único de mensaje

Todos los canales usan exactamente el mismo flujo. Sin excepciones.

```
Canal (Web / WhatsApp / IG / Messenger / API)
        ↓  adaptador -> InboundMessage normalizado
      API REST
        ↓
      Core  (tenant → contexto → intención)
        ↓
     Plugin (si aplica)
        ↓
     Respuesta  → adaptador de salida → Canal
```

Agregar un canal nuevo = escribir un adaptador en `/channels`. Nada más cambia.

---

## 5. Multi-tenancy

- Toda tabla con datos de empresa lleva `company_id` (FK, indexado, **NOT NULL**).
- El `company_id` se resuelve en middleware desde el JWT o el token de canal, y viaja en el contexto de request. **Nunca** se acepta desde el body.
- Toda query pasa por un repositorio/dependencia que filtra por `company_id`. Está prohibido escribir queries sin filtro de tenant.
- Row Level Security en PostgreSQL como segunda barrera.
- Claves de Redis siempre prefijadas: `tenant:{company_id}:...`
- Antes de dar por terminado un endpoint: verificar que un tenant no pueda leer ni escribir datos de otro.

---

## 6. Datos del negocio (dominio del Core)

Entidades estructuradas que la empresa administra por formularios y que alimentan las respuestas de la IA:

| Entidad | Campos principales |
|---|---|
| **Empresa** | nombre, logo, descripción, rubro, teléfono, email, dirección, sitio web, redes sociales |
| **Servicio** | nombre, categoría, descripción, precio, tiempo estimado, imagen, estado |
| **Producto** | nombre, descripción, precio, código, imagen, stock (opcional), estado |
| **Horario** | atención semanal, excepciones, feriados, sucursales |
| **Promoción** | nombre, descripción, fecha inicio, fecha término, condiciones, activa |
| **Política** | tipo (pagos, garantías, devoluciones, reservas, privacidad), contenido |
| **FAQ** | pregunta, respuesta, categoría |

Cada registro es independiente (CRUD completo). Nada se almacena como texto libre no estructurado destinado a la IA.

---

## 7. Backend — componentes obligatorios

**Autenticación:** JWT (access corto) + refresh token rotativo, roles, permisos.
**Gestión multiempresa:** empresas, usuarios, permisos, configuraciones.
**Conversaciones:** chats, mensajes, contexto, historial, asignación a operador.
**API REST:** *toda* funcionalidad expuesta como API. El frontend nunca accede a la base de datos ni a servicios internos directamente.
**Motor IA:** recibir mensaje → detectar intención → consultar información → ejecutar plugin → responder.
**Plugin Manager:** detectar, instalar, actualizar, desinstalar, ejecutar, gestionar permisos.
**Motor de Canales:** adaptadores que normalizan entrada/salida al mismo contrato.
**Caché Redis:** conversaciones, sesiones, información del negocio, rate limit. Invalidación explícita al editar datos del tenant.
**Auditoría:** usuarios, conversaciones, errores, plugins ejecutados, acciones administrativas.
**Logs:** estructurados en JSON, con `request_id`, `company_id`, `user_id`, latencia y métricas.

---

## 8. Sistema de plugins

Los plugins se cargan **in-process**: el Plugin Manager descubre módulos en `/plugins`, valida el manifiesto y los registra.

### Contrato obligatorio

Todo plugin implementa la misma interfaz:

```python
class PluginInterface(Protocol):
    manifest: PluginManifest

    async def install(self, ctx: PluginContext) -> None: ...
    async def update(self, ctx: PluginContext) -> None: ...
    async def uninstall(self, ctx: PluginContext) -> None: ...
    async def configure(self, ctx: PluginContext, config: dict) -> None: ...
    async def execute(self, ctx: PluginContext, intent: Intent) -> PluginResult: ...
    async def check_permissions(self, ctx: PluginContext, action: str) -> bool: ...
```

`PluginContext` entrega al plugin: `company_id`, usuario, sesión de DB, caché, config del plugin y logger. **El plugin nunca importa módulos internos del Core fuera de la API pública de `plugins_runtime`.**

### Manifiesto

```json
{
  "name": "agenda",
  "version": "1.0.0",
  "author": "",
  "description": "",
  "category": "productividad",
  "dependencies": [],
  "permissions": ["conversations.read", "agenda.write"],
  "hooks": ["message.received", "conversation.closed"],
  "screens": [{ "path": "/agenda", "label": "Agenda", "icon": "calendar" }]
}
```

### Reglas de plugin

- Tablas propias, con prefijo `plg_<nombre>_`. **Nunca** modificar ni alterar tablas del Core.
- Migraciones propias, dentro del plugin.
- Endpoints propios bajo `/api/v1/plugins/<nombre>/...` (ej. `/agenda`, `/cotizaciones`, `/crm`).
- Toda la lógica del plugin vive en el plugin.
- Puede declarar pantallas nuevas para el panel administrativo (ej. Agenda → calendario, horarios, reservas).
- Administra sus propios permisos.
- Escucha eventos: `customer.created`, `conversation.started`, `booking.created`, `quote.sent`, etc.
- Hooks del sistema: al llegar un mensaje, al cerrar una conversación, al crear una reserva, al crear un usuario.
- Integraciones externas propias: Google Calendar, Outlook, Stripe, WhatsApp, Meta, Google Meet.
- Credenciales del plugin se guardan cifradas por tenant, nunca en el repo.
- Un plugin que falla **no puede** tumbar el Core: ejecución con timeout, captura de excepciones y respuesta degradada.

---

## 9. Frontend — panel administrativo

Secciones:

- **Dashboard** — resumen, estado del sistema, conversaciones, plugins instalados, estadísticas
- **Empresa** — información general
- **Servicios** — listar / agregar / editar / eliminar
- **Productos** — listar / agregar / editar / eliminar
- **Horarios** — atención, excepciones, feriados, sucursales
- **Promociones**
- **Políticas** — pagos, garantías, devoluciones, reservas, privacidad
- **FAQ**
- **Plugins** — ver, instalar, desinstalar, configurar, activar, desactivar
- **Canales** — Web, WhatsApp, Instagram, Messenger, Telegram, API
- **Conversaciones** — historial, búsqueda, filtros, asignaciones
- **Usuarios** — administradores, operadores, permisos
- **Configuración** — idioma, zona horaria, configuración IA, seguridad, tokens

Reglas:

- El frontend consume **solo** la API REST. Cero lógica de negocio.
- Tipos TypeScript generados desde el OpenAPI del backend; no escribir tipos a mano.
- Las pantallas de plugins se renderizan dinámicamente desde el registro de plugins.
- Diseño responsive, accesible, y pensado para usuarios sin conocimientos técnicos.

---

## 10. Integración con proyectos externos

Esta sección define cómo un proyecto ajeno consume la plataforma. Es tan importante como el Core.

### 10.1 Superficie pública

| Superficie | Para qué | Ruta |
|---|---|---|
| **API REST pública** | Que otro backend consulte y converse con el asistente | `/api/v1/public/...` |
| **Widget embebible** | Que otra web tenga chat con una línea de código | `/widget/v1/embed.js` |
| **Webhooks salientes** | Que el proyecto externo reciba eventos en tiempo real | configurables por tenant |
| **SDKs oficiales** | Integración en 3 líneas | `/sdk/python`, `/sdk/javascript` |
| **OpenAPI + docs** | Contrato autodescriptivo | `/api/v1/openapi.json`, `/docs` |

Separación clara de espacios de la API:

- `/api/v1/admin/...` → panel administrativo. Autenticación JWT de usuario.
- `/api/v1/public/...` → proyectos externos. Autenticación por **API key**.
- `/api/v1/channels/...` → webhooks entrantes de WhatsApp, Meta, etc.
- `/api/v1/plugins/<nombre>/...` → endpoints de plugins (pueden exponerse en admin y/o public).

### 10.2 Autenticación de terceros

- **API keys por empresa**, con prefijo visible de entorno: `sk_live_...`, `sk_test_...`
- Se guardan **hasheadas** (nunca en claro). Se muestran una sola vez al crearlas.
- Cada key tiene: nombre, **scopes**, entorno, rate limit, IPs permitidas (opcional), fecha de expiración, último uso.
- Scopes granulares: `chat:write`, `conversations:read`, `catalog:read`, `catalog:write`, `plugins:execute`, `webhooks:manage`.
- Rotación sin downtime: se pueden tener 2 keys activas simultáneas.
- Se envía en header: `Authorization: Bearer sk_live_...`
- Para el widget en navegador se usa una **public key** (`pk_...`) de solo-chat, con dominios permitidos. **Nunca** una secret key en el frontend de un tercero.
- La API key determina el `company_id`. El tenant **jamás** se acepta como parámetro.

### 10.3 Integración mínima (debe seguir siendo así de simple)

**Web de terceros — una línea:**

```html
<script src="https://cdn.tuplataforma.com/widget/v1/embed.js"
        data-key="pk_live_xxx" defer></script>
```

**Backend de terceros — una llamada:**

```bash
curl -X POST https://api.tuplataforma.com/api/v1/public/chat \
  -H "Authorization: Bearer sk_live_xxx" \
  -H "Content-Type: application/json" \
  -d '{
        "conversation_id": "opcional",
        "external_user_id": "user-123",
        "message": "¿A qué hora abren el sábado?"
      }'
```

**SDK:**

```python
from asistente import Client
client = Client(api_key="sk_live_xxx")
resp = client.chat.send(message="¿A qué hora abren?", external_user_id="user-123")
print(resp.reply)
```

Si una integración básica requiere más que esto, hay que simplificar la API, no documentar más.

### 10.4 Endpoints públicos base

```
POST   /api/v1/public/chat                     # enviar mensaje, recibir respuesta
GET    /api/v1/public/conversations            # listar
GET    /api/v1/public/conversations/{id}       # historial
POST   /api/v1/public/conversations/{id}/close
GET    /api/v1/public/company                  # datos del negocio
GET    /api/v1/public/services
GET    /api/v1/public/products
GET    /api/v1/public/schedule
GET    /api/v1/public/promotions
GET    /api/v1/public/faq
POST   /api/v1/public/plugins/{name}/execute   # ejecutar acción de plugin
GET    /api/v1/public/health
```

Los plugins pueden añadir endpoints públicos propios declarándolos en su manifiesto.

### 10.5 Identidad de usuarios externos

El proyecto que integra ya tiene sus propios usuarios. La plataforma **no** los reemplaza:

- El tercero envía `external_user_id` (su ID) y opcionalmente `external_metadata`.
- La plataforma crea/reutiliza un contacto vinculado a ese ID dentro del tenant.
- Nunca se pide al usuario final que se registre en esta plataforma.

### 10.6 Webhooks salientes

- Configurables por empresa desde el panel y desde la API.
- Eventos: `message.received`, `message.replied`, `conversation.started`, `conversation.closed`, `handoff.requested`, `plugin.executed`, más los que declaren los plugins.
- Payload JSON firmado con HMAC-SHA256 en header `X-Signature` + `X-Timestamp` (protección contra replay).
- Reintentos con backoff exponencial, cola en Redis, DLQ y log de entregas visible en el panel.
- Cada envío lleva `event_id` único para que el receptor deduplique.

### 10.7 Reglas del contrato público

- **Versionado en la URL.** `v1` no se rompe nunca. Cambios incompatibles → `v2`.
- Solo se permiten cambios **aditivos** dentro de una versión: campos nuevos opcionales, endpoints nuevos. Prohibido renombrar o eliminar campos.
- Deprecaciones anunciadas con header `Sunset` y al menos 6 meses de aviso.
- **Idempotencia:** todo `POST` que crea algo acepta `Idempotency-Key`.
- Errores con formato estable y códigos legibles:
  ```json
  { "error": { "code": "invalid_api_key", "message": "...", "request_id": "req_..." } }
  ```
- Rate limit informado siempre en headers `X-RateLimit-Limit`, `-Remaining`, `-Reset`; `429` con `Retry-After`.
- Paginación por cursor consistente en todos los listados.
- CORS restringido a los dominios que la empresa registró.
- Entorno **sandbox** (`sk_test_`) con datos aislados, para que cualquiera pruebe sin tocar producción.
- El OpenAPI se genera automáticamente y se valida en CI: si el contrato cambia sin subir versión, el build falla.

### 10.8 Al construir cualquier feature, pregunta

1. ¿Es consumible por un proyecto externo sin acceso interno?
2. ¿Está en `/public` con scope y rate limit definidos?
3. ¿Emite un webhook si otro sistema necesitaría enterarse?
4. ¿Aparece en el OpenAPI y en los SDKs?
5. ¿Rompe el contrato `v1`? Si sí, no se hace.

---

## 11. Convenciones de código

**Python**

- `async` en todo I/O. Nada de llamadas bloqueantes en el event loop.
- Type hints obligatorios. `mypy` en modo estricto.
- Formato con `ruff format`, lint con `ruff`.
- Capas: `route → service → repository → model`. Las rutas no contienen lógica.
- Schemas Pydantic separados: `...Create`, `...Update`, `...Read`.
- Errores de dominio como excepciones propias, traducidas a HTTP en un handler central.
- Configuración solo vía `pydantic-settings` + variables de entorno. Sin secretos en el código.

**TypeScript**

- `strict: true`. Nada de `any`.
- Server Components por defecto; `"use client"` solo cuando hace falta.
- Componentes pequeños y colocalizados por feature.

**Base de datos**

- snake_case, plural en tablas del Core.
- Toda tabla: `id` (UUID), `created_at`, `updated_at`, y `company_id` cuando aplique.
- Todo cambio de esquema pasa por Alembic. Nunca modificar la base a mano.

**API**

- Versionada: `/api/v1/...`
- Respuestas y errores con formato consistente.
- Paginación por cursor en listados largos.

**Git**

- Conventional Commits: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`
- Una rama por feature. PR con tests.

---

## 12. Comandos

```bash
# Entorno completo
docker compose up -d

# Backend
cd backend
uv sync                       # o: pip install -r requirements.txt
uvicorn app.main:app --reload
alembic revision --autogenerate -m "descripcion"
alembic upgrade head
pytest
ruff check . && ruff format . && mypy app

# Frontend
cd frontend
npm install
npm run dev
npm run lint && npm run typecheck && npm run build
```

---

## 13. Prohibiciones

No hagas nada de esto sin discutirlo primero:

- ❌ Poner lógica de negocio en el Core
- ❌ Acoplar el Core a un plugin específico
- ❌ Que un plugin toque tablas del Core
- ❌ Queries sin filtro de `company_id`
- ❌ Frontend accediendo a la base de datos o saltándose la API
- ❌ Ingesta de PDFs/archivos, embeddings, vector DB o fine-tuning como fuente de conocimiento
- ❌ Lógica distinta por canal (todos comparten el mismo flujo)
- ❌ Secretos, tokens o credenciales en el repositorio
- ❌ Cambios de esquema fuera de Alembic
- ❌ Referencias a FinopsLatam, ClienteFiel, Riava o cualquier producto concreto dentro del código
- ❌ Romper el contrato público `v1` (renombrar/eliminar campos, cambiar tipos, cambiar semántica)
- ❌ Aceptar `company_id` desde el cliente en endpoints públicos
- ❌ Exponer una secret key (`sk_`) en código de frontend de terceros
- ❌ Funcionalidad accesible solo desde el panel y no desde la API pública
- ❌ Obligar al usuario final de un proyecto externo a registrarse en esta plataforma

---

## 14. Checklist antes de terminar una tarea

1. ¿Esto es Core o plugin? ¿Está en el lugar correcto?
2. ¿Todas las queries filtran por `company_id`?
3. ¿Los permisos RBAC están verificados en el endpoint?
4. ¿Hay auditoría y logs estructurados de la acción?
5. ¿Existe migración Alembic si cambió el esquema?
6. ¿Hay tests (unitarios + al menos uno de aislamiento entre tenants)?
7. ¿Pasan `ruff`, `mypy`, `pytest`, `npm run typecheck` y `build`?
8. ¿La caché se invalida cuando corresponde?
9. ¿La documentación OpenAPI quedó correcta?
10. ¿Un proyecto externo puede usar esto vía API pública, con scope y rate limit?
11. ¿Se emite webhook si otro sistema necesita enterarse?
12. ¿El contrato `v1` sigue intacto?
13. ¿El Core sigue siendo pequeño?

---

## 15. Objetivo final

Construir una plataforma de asistentes digitales empresariales que funcione como **servicio consumible por otros proyectos**: Core pequeño, estable y reutilizable; capacidades específicas incorporadas mediante plugins independientes; y una API pública versionada, documentada y trivial de integrar. Cada empresa administra su información desde un panel intuitivo y conecta el asistente a distintos canales y sistemas externos sin modificar el núcleo. La arquitectura debe permitir evolucionar durante años e integrarse con cualquier desarrollo futuro sin sacrificar mantenibilidad, rendimiento ni seguridad.
