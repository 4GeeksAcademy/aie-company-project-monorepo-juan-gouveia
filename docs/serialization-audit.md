# Auditoría de serialización — Brasaland API

Esta auditoría revisa todos los endpoints de `services/brasaland-api` (FastAPI) antes de que la API reciba usuarios reales. Para cada endpoint registra:

- qué recibe;
- qué devuelve hoy;
- qué lee de verdad su consumidor;
- qué debería devolver.

La clasificación de partida se conserva. Después se registran los cambios aplicados y la verificación.

- **Rama:** `feature/serialization-audit`.
- **Fecha de la auditoría inicial:** 2026-11-18.
- **Estado:** completada (2026-11-18). La auditoría inicial (Fase 1) se conserva en las secciones 2 a 6; los cambios aplicados (Fase 2) están en la sección 7 y la verificación (Fase 3) en la sección 8. Los 35 endpoints quedan ✅.

## 1. Método

1. **Inventario.** Se extrajeron las operaciones del esquema OpenAPI generado por la propia aplicación (`app.openapi()`) y se contrastaron con los decoradores de los routers. Salen **35 operaciones**: 34 bajo `/api/v1` y `GET /health`.
2. **Comportamiento actual.** Para cada handler se revisó:
   - si declara `response_model`;
   - qué objeto devuelve realmente (ORM, `dict` o esquema Pydantic);
   - cómo se construye ese objeto;
   - qué esquema valida la entrada.
3. **Consumidores.** El único consumidor de la API es el backoffice (`uis/backoffice`), a través de su intermediario BFF (`app/api/[...path]/route.ts`). Se siguió cada llamada desde `lib/` y `hooks/` hasta los componentes y se anotaron los campos que lee cada pantalla. El website no llama a la API. La herramienta de talento del backoffice (`lib/talento/api.ts`) usa otra API externa (`NEXT_PUBLIC_API_BASE_URL`) y queda fuera del alcance.
4. **Clasificación.** Cada endpoint recibe uno de estos estados:
   - ✅ **Ya serializado:** tiene un `response_model` explícito y el esquema es adecuado para su consumidor.
   - ⚠️ **Parcialmente serializado:** tiene `response_model`, pero expone campos innecesarios o internos, o no coincide con lo que necesita el cliente.
   - ❌ **Sin serializar:** devuelve un objeto ORM en crudo o un `dict` sin tipo.
5. **Criterios de salida.** Hay seis:
   - nunca contraseñas, ni en texto plano ni hasheadas, ni tokens internos;
   - las rutas de auth no autenticadas (registro, login, forgot/reset) no reenvían el email;
   - `GET /auth/me` sí puede devolver el email del propio usuario;
   - los listados devuelven solo lo que usa la pantalla;
   - sin objetos anidados completos cuando basta una proyección plana;
   - sin claves foráneas duplicadas junto al objeto anidado que ya las contiene.
6. **Criterios de entrada.** Cada escritura (POST, PUT, PATCH) tiene un esquema de entrada propio, distinto del de salida, que solo acepta los campos que el cliente puede escribir (`extra="forbid"`).

## 2. Resumen

| Estado original | Endpoints | % |
|---|---|---|
| ✅ Ya serializado | 23 | 66 % |
| ⚠️ Parcialmente serializado | 10 | 29 % |
| ❌ Sin serializar | 1 | 3 % |
| Excepción documentada (archivo CSV) | 1 | 3 % |
| **Total** | **35** | |

**Estado final (Fase 3, 2026-11-18):** los 35 endpoints quedan ✅. 34 tienen un esquema de respuesta con nombre y la exportación CSV (I2) declara `response_model=None` como excepción documentada. La guarda `tests/integration/test_response_models.py` lo mantiene (sección 7, 2d).

Conclusiones principales:

- **Ningún endpoint devuelve un objeto ORM en crudo.**
  - El inventario (SQLModel + Supabase) convierte cada fila en un esquema de lectura (`IngredientRead`, `IngredientEntryRead`…) dentro de `service.py`, antes de llegar al router.
  - Los dominios en TinyDB validan cada documento contra un modelo Pydantic.
  - Los usuarios pasan siempre por `User.to_public()`, que excluye `hashed_password` y `password_changed_at`.
- **Ninguna respuesta incluye contraseñas ni tokens internos.** Los únicos tokens que salen son los JWT de acceso de `POST /auth/login` y `POST /auth/change-password`, que son precisamente lo que el cliente necesita.
- **Todas las escrituras tienen ya un esquema de entrada separado** con `extra="forbid"`. Ninguna reutiliza un esquema de salida.
- **El trabajo pendiente es de forma, no de seguridad grave:**
  - el registro reenvía el email, cosa que el briefing no permite;
  - el perfil expone identificadores internos;
  - el listado de incidencias reutiliza el esquema de detalle;
  - las órdenes del inventario anidan el ingrediente completo junto a su clave foránea;
  - `GET /health` devuelve un `dict` sin tipo.

## 3. Tabla general

La tabla conserva el estado original de la auditoría y añade, en las dos últimas columnas, el esquema y el estado tras la Fase 2.

**Leyenda:**

- **Auth:** `—` = pública; `JWT` = requiere token; `admin` = solo administradores.
- **Consumidor:** el archivo del backoffice que llama a la ruta. "API" significa que no hay pantalla que la use (clientes de la API, administración o pruebas).

| # | Método y ruta | Propósito | Auth | Entrada | `response_model` original | Consumidor | Estado original | `response_model` final | Estado final |
|---|---|---|---|---|---|---|---|---|---|
| A1 | `POST /api/v1/auth/login` | Iniciar sesión | — | `LoginRequest` | `Token` | `lib/auth/api.ts` | ✅ | sin cambios | ✅ |
| A2 | `GET /api/v1/auth/me` | Usuario de la sesión y su perfil | JWT | — | `CurrentUser` | `AccountMenu`, `AccountProfile`, `OrdersPanel` | ⚠️ | `CurrentUser` (perfil `ProfileRead`) — 2a | ✅ |
| A3 | `POST /api/v1/auth/forgot-password` | Pedir el enlace de restablecimiento | — | `ForgotPasswordRequest` | `MessageResponse` | `lib/auth/api.ts` | ✅ | sin cambios | ✅ |
| A4 | `POST /api/v1/auth/reset-password/validate` | Validar el enlace antes de pintar el formulario | — | `ResetTokenCheck` | `MessageResponse` | `lib/auth/api.ts` | ✅ | sin cambios | ✅ |
| A5 | `POST /api/v1/auth/reset-password` | Fijar una contraseña nueva con el enlace | — | `ResetPasswordRequest` | `MessageResponse` | `lib/auth/api.ts` | ✅ | sin cambios | ✅ |
| A6 | `POST /api/v1/auth/change-password` | Cambiar la contraseña con la sesión iniciada | JWT | `ChangePasswordRequest` | `PasswordChanged` | `ChangePasswordForm` | ✅ | sin cambios | ✅ |
| U1 | `POST /api/v1/users` | Registro | — | `UserCreate` | `UserWithProfile` | `RegisterForm` | ⚠️ | `UserCreated` — 2a | ✅ |
| U2 | `GET /api/v1/users` | Listar cuentas | admin | — | `list[UserPublic]` | API | ✅ | sin cambios | ✅ |
| U3 | `GET /api/v1/users/{user_id}` | Ver una cuenta | JWT (propia o admin) | — | `UserPublic` | API | ✅ | sin cambios | ✅ |
| U4 | `PUT /api/v1/users/{user_id}` | Cambiar credenciales, rol o estado | JWT (propia o admin) | `UserUpdate` | `UserPublic` | API | ✅ | sin cambios | ✅ |
| U5 | `DELETE /api/v1/users/{user_id}` | Borrar una cuenta y su perfil | JWT (propia o admin) | — | `UserPublic` | API | ✅ | sin cambios | ✅ |
| P1 | `GET /api/v1/profiles/me` | Perfil propio | JWT | — | `Profile` | API | ⚠️ | `ProfileRead` — 2a | ✅ |
| P2 | `PUT /api/v1/profiles/me` | Editar el perfil propio | JWT | `ProfileUpdate` | `Profile` | `ProfileForm` | ⚠️ | `ProfileRead` — 2a | ✅ |
| P3 | `GET /api/v1/profiles/{user_id}` | Perfil de una cuenta | JWT (propio o admin) | — | `Profile` | API | ⚠️ | `ProfileRead` — 2a | ✅ |
| P4 | `PUT /api/v1/profiles/{user_id}` | Editar un perfil por usuario | JWT (dueño) | `ProfileUpdate` | `Profile` | API | ⚠️ | `ProfileRead` — 2a | ✅ |
| I1 | `POST /api/v1/incidents/analyze` | Analizar el CSV de incidentes | JWT | `multipart` (`file`) | `AnalysisResponse` | `IncidentAnalysisPanel` y subcomponentes | ✅ | sin cambios | ✅ |
| I2 | `GET /api/v1/incidents/results/export` | Descargar `results.csv` | JWT | — | ninguno (`response_class=Response`, `text/csv`) | `lib/incidencias/api.ts` | Excepción | `None` explícito, `text/csv` — 2c | ✅ (excepción documentada) |
| I3 | `POST /api/v1/incidents` | Registrar una incidencia | JWT | `IncidentCreate` | `Incident` | `IncidentForm` | ✅ | sin cambios | ✅ |
| I4 | `GET /api/v1/incidents` | Listar incidencias con filtros | JWT | query `status`, `origin`, `branch`, `category` | `list[Incident]` | `IncidentList` | ⚠️ | `list[IncidentListItem]` — 2c | ✅ |
| I5 | `GET /api/v1/incidents/summary` | Métricas del gestor | JWT | — | `IncidentSummary` | `IncidentSummaryPanel` | ✅ | sin cambios | ✅ |
| I6 | `GET /api/v1/incidents/{incident_id}` | Detalle de una incidencia | JWT | — | `Incident` | API | ✅ | sin cambios | ✅ |
| I7 | `PATCH /api/v1/incidents/{incident_id}/status` | Cambiar el estado | JWT | `StatusUpdate` | `Incident` | `IncidentStatusControl` | ✅ | sin cambios | ✅ |
| S1 | `POST /api/v1/suppliers` | Alta de proveedor | JWT | `SupplierCreate` | `Supplier` | `SupplierFormModal` | ✅ | sin cambios | ✅ |
| S2 | `GET /api/v1/suppliers` | Directorio con filtros | JWT | query `country`, `category` | `list[Supplier]` | `SupplierList`, `lib/inventory-suppliers.ts` | ✅ | sin cambios | ✅ |
| S3 | `GET /api/v1/suppliers/{supplier_id}` | Detalle de un proveedor | JWT | — | `Supplier` | API | ✅ | sin cambios | ✅ |
| S4 | `DELETE /api/v1/suppliers/{supplier_id}` | Borrar un proveedor | JWT | — | `Supplier` | API | ✅ | sin cambios | ✅ |
| S5 | `PATCH /api/v1/suppliers/{supplier_id}/rate` | Actualizar la tarifa | JWT | `RateUpdate` | `Supplier` | `RateEditor` | ✅ | sin cambios | ✅ |
| S6 | `PATCH /api/v1/suppliers/{supplier_id}/status` | Activar o suspender | JWT | `StatusUpdate` | `Supplier` | `StatusToggle` | ✅ | sin cambios | ✅ |
| N1 | `GET /api/v1/inventory/products` | Catálogo con stock calculado | JWT | query `country` | `list[IngredientRead]` | `IngredientTable`, `IngredientSelect` | ✅ | sin cambios | ✅ |
| N2 | `POST /api/v1/inventory/products` | Alta de ingrediente | JWT | `IngredientCreate` | `IngredientRead` | API | ✅ | sin cambios | ✅ |
| N3 | `GET /api/v1/inventory/products/{ingredient_id}` | Stock de un ingrediente | JWT | — | `IngredientRead` | `useIngredientStock` | ✅ | sin cambios | ✅ |
| N4 | `POST /api/v1/inventory/orders/inbound` | Registrar una entrada | JWT | `IngredientEntryCreate` | `IngredientEntryRead` | `EntryForm` | ⚠️ | `IngredientEntryRead` plano — 2b | ✅ |
| N5 | `POST /api/v1/inventory/orders/outbound` | Registrar una salida | JWT | `IngredientExitCreate` | `IngredientExitRead` | `ExitForm` | ⚠️ | `IngredientExitRead` plano — 2b | ✅ |
| N6 | `GET /api/v1/inventory/orders` | Historial de entradas y salidas | JWT | — | `OrdersRead` | `OrderHistory` | ⚠️ | `OrdersRead` plano — 2b | ✅ |
| H1 | `GET /health` | Comprobación de vida | — | — | ninguno (`dict[str, str]`) | Docker / supervisión | ❌ | `HealthResponse` — 2c | ✅ |

## 4. Fichas por dominio

Las rutas de autenticación van primero porque son las de mayor riesgo. En cada ficha, **Hoy** es lo que sale ahora, **Usa** es lo que lee el consumidor y **Objetivo** es el payload de salida acordado, con la lista explícita de campos.

### 4.1 Autenticación (`/auth`) y registro (`/users`)

Comprobaciones del briefing sobre las rutas no autenticadas:

| Ruta | ¿Devuelve contraseña? | ¿Reenvía el email? | Resultado |
|---|---|---|---|
| A1 `POST /auth/login` | No | No: `{access_token, token_type}` | ✅ |
| A3 `POST /auth/forgot-password` | No | No: mensaje genérico ("Si esa dirección está registrada…"), igual exista o no la cuenta | ✅ |
| A4 `POST /auth/reset-password/validate` | No | No | ✅ |
| A5 `POST /auth/reset-password` | No | No | ✅ |
| U1 `POST /users` (registro) | No | **Sí** | ⚠️ |

**A1 `POST /auth/login` — ✅.**
- **Hoy:** `Token` = `access_token`, `token_type`.
- **Usa:** `RegisterForm` y `LoginForm` leen `access_token` y lo guardan.
- No hay nada que cambiar.

**A2 `GET /auth/me` — ⚠️ expone identificadores internos del perfil.**
- **Hoy:** `CurrentUser` = `id`, `email`, `role`, `profile{id, user_id, name, phone, address}`.
- **Usa:**
  - `id`, para marcar "mis órdenes" en `OrderHistory`;
  - `email`, en `AccountMenu` y `AccountProfile`;
  - `profile.name`, `profile.phone` y `profile.address`, en `AccountMenu` y `ProfileForm`;
  - `profile.id`, solo como `key` de React para reiniciar el formulario si cambia la cuenta.
- **`role`:** ninguna pantalla lo lee hoy. Se mantiene porque es la autorización del propio usuario, y los permisos por rol figuran como pendientes en `docs/ARCHITECTURE_PROPOSAL.md`. Es un campo de una sola cuenta, no un listado.
- **Por qué cambia:**
  - `profile.user_id` repite `id`;
  - `profile.id` es un UUID interno que ninguna ruta acepta, porque los perfiles se direccionan por `user_id`;
  - la `key` de React puede usar `user.id`, que identifica igual la cuenta.
- **Objetivo:** `CurrentUser` = `id`, `email`, `role`, `profile: ProfileRead | null`, con `ProfileRead` = `name`, `phone`, `address`. El email sí se devuelve, porque el briefing lo permite en `/auth/me` y la vista de cuenta lo muestra.
- **Relación:** el perfil sigue **anidado** como una proyección reducida, sin identificadores. Es una relación 1:1 que el formulario de perfil edita como un bloque, así que aplanarlo en `CurrentUser` solo mezclaría credenciales y datos de contacto.

**A3, A4 y A5 — ✅.** Devuelven `MessageResponse` = `message`. El backoffice muestra el texto o solo comprueba el 200. No hay nada que cambiar.

**A6 `POST /auth/change-password` — ✅.**
- **Hoy:** `PasswordChanged` = `access_token`, `token_type`, `message`.
- **Usa:** `ChangePasswordForm` guarda el token nuevo (el anterior queda invalidado por `password_changed_at`) y muestra el mensaje.
- No incluye email ni contraseña. No hay nada que cambiar.

**U1 `POST /users` (registro) — ⚠️ reenvía el email y datos que el cliente no usa.**
- **Hoy:** `UserWithProfile` = `id`, `email`, `is_active`, `role`, `created_at`, `profile{id, user_id, name, phone, address}`.
- **Usa:** nada. `RegisterForm` solo comprueba el 201 y después inicia sesión con el email y la contraseña que ya tiene en el formulario.
- **Por qué cambia:**
  - el briefing prohíbe reenviar el email en el registro;
  - el resto son datos que el cliente acaba de enviar (perfil) o detalles internos de la cuenta (`is_active`, `role`, `created_at`) que no necesita para el paso siguiente.
- **Objetivo (decisión D3):** `UserCreated` = `id`, `message` ("Cuenta creada."). El `id` identifica el recurso creado en un 201, y el mensaje confirma la operación.
- **Entrada:** `UserCreate` (`email`, `password`, `name`, `phone`, `address`; `extra="forbid"`) no cambia. No acepta `role` ni `is_active`: todo registro empieza con rol `user`.

### 4.2 Usuarios (`/users`, salvo el registro)

**U2–U5 — ✅.**
- **Hoy:** `UserPublic` = `id`, `email`, `is_active`, `role`, `created_at`, construido con `User.to_public()`. Es un esquema con atributos explícitos que excluye `hashed_password` y `password_changed_at`.
- **Quién las llama:** son rutas de administración o del propio usuario, todas autenticadas: U2 solo admin, U3–U5 la cuenta propia o un admin. Aquí el email sí es necesario, porque es la credencial que se gestiona.
- **Entrada de U4:** `UserUpdate` (`email`, `password`, `role`, `is_active`; todos opcionales; `extra="forbid"`). El router rechaza con 403 `role` e `is_active` si quien llama no es admin. Ese control es de autorización, no de esquema, y ya tiene pruebas. No hay nada que cambiar.
- **U5 `DELETE`** devuelve la cuenta borrada, como confirmación del recurso eliminado. No hay credenciales en la respuesta.
- **Nota de diseño (sin cambio):** el modelo interno `User` hereda de `UserPublic` y añade los campos sensibles. Hoy es seguro porque todos los handlers devuelven `to_public()` y declaran `response_model=UserPublic`. La prueba de guarda de la Fase 2 (sección 6) impide que una ruta nueva quede sin `response_model` y acabe devolviendo `User`.

### 4.3 Perfiles (`/profiles`)

**P1–P4 — ⚠️ exponen `id` y `user_id`.**
- **Hoy:** `Profile` = `id`, `user_id`, `name`, `phone`, `address`.
- **Usa:**
  - P2, desde `ProfileForm`: `name`, `phone` y `address`, que pasa a `AccountProfile` para refrescar la sesión;
  - P1, P3 y P4 no tienen pantalla.
- **Por qué cambia:**
  - `id` es un UUID interno que ninguna ruta acepta;
  - `user_id` es la clave foránea al usuario, y quien llama ya la conoce: es él mismo en `/me` o el valor de la URL en `/{user_id}`.
- **Objetivo:** `ProfileRead` = `name`, `phone`, `address`, el mismo esquema que va anidado en `/auth/me`. Las cuatro rutas comparten exactamente esa proyección segura, así que un esquema común es válido.
- **Entrada:** `ProfileUpdate` (`name`, `phone`, `address`; `extra="forbid"`) ya es un esquema distinto del de salida. No hay nada que cambiar.

### 4.4 Incidencias: analizador (`/incidents/analyze` y exportación)

**I1 `POST /incidents/analyze` — ✅.**
- **Hoy:** `AnalysisResponse` contiene los totales, `invalid_breakdown`, `invalid_records_detail`, `categories`, `statuses` y `satisfaction`.
- **Usa:** `IncidentAnalysisPanel`, `SummaryCards`, `BreakdownTable`, `InvalidRecordsNotice` y `SatisfactionPanel` leen todos los bloques.
- Los valores coinciden exactamente con los esperados en el briefing del procesador de incidentes. No hay nada que cambiar.

**I2 `GET /incidents/results/export` — excepción documentada (decisión D2).**
- **Hoy:** devuelve el archivo `results.csv` (`text/csv`, `Content-Disposition: attachment`) con `response_class=Response`, sin `response_model`.
- **Por qué no lleva esquema Pydantic:** la respuesta es un archivo, no JSON. El briefing del analizador exige la descarga de `results.csv`, y un `response_model` no puede describir un CSV.
- **Objetivo:**
  - declarar `response_model=None` de forma explícita en el decorador, para que la ausencia de esquema sea una decisión visible y no un olvido;
  - mantener documentado en OpenAPI el contenido `text/csv` (columnas `metric`, `value`, `percentage`);
  - registrar la excepción en `docs/BRIEFING_DIVERGENCES.md`.
- La prueba de guarda la acepta como única excepción, con nombre propio.

### 4.5 Incidencias: gestor (`/incidents`)

**I3 `POST /incidents` — ✅.**
- **Hoy:** devuelve `Incident` = `id`, `title`, `description`, `category`, `status`, `origin`, `branch`, `created_at`, `updated_at`.
- **Usa:** `IncidentForm` lee `id`, `title` y `status`, y el hook inserta la incidencia en la lista.
- Devolver el recurso creado completo es la confirmación estándar de un alta.
- **Entrada:** `IncidentCreate` no acepta `id` ni las fechas. `status` es opcional y solo admite `open`.

**I4 `GET /incidents` — ⚠️ el listado reutiliza el esquema de detalle.**
- **Hoy:** `list[Incident]`, con `updated_at` en cada fila.
- **Usa:** `IncidentList` muestra `id`, `title`, `description`, `category`, `status`, `origin`, `branch` y `created_at`. Ninguna pantalla lee `updated_at`.
- **Por qué cambia:** el briefing pide un esquema propio y más ligero para los listados, y no reutilizar el de detalle por defecto. `updated_at` es un timestamp de auditoría útil en el detalle (I6), pero en el listado solo engorda cada fila.
- **Objetivo:** `IncidentListItem` = `id`, `title`, `description`, `category`, `status`, `origin`, `branch`, `created_at`. `Incident`, el detalle, sigue teniendo `updated_at`.
- **Nota:** el listado no tiene paginación. Hoy el volumen es bajo. Queda anotado como mejora futura (sección 9), fuera del alcance de la serialización.

**I5 `GET /incidents/summary` — ✅.** `IncidentSummary` = `total`, `by_status`, `by_category`, `by_origin`, `by_branch`. Son agregados y no hay campos de más.

**I6 `GET /incidents/{id}` — ✅.** Es una vista de detalle y devuelve el recurso completo, con `updated_at`. Todos sus campos son públicos para el equipo.

**I7 `PATCH /incidents/{id}/status` — ✅.**
- Devuelve `Incident`. `useIncidents` sustituye la fila por la respuesta.
- `Incident` es un superconjunto de `IncidentListItem`, así que el campo extra (`updated_at`) no rompe la lista.
- **Entrada:** `StatusUpdate` = `status`, con `extra="forbid"`.

### 4.6 Proveedores (`/suppliers`)

**S1–S6 — ✅.**
- **Hoy:** `Supplier` = `id`, `name`, `country`, `categories`, `rate_per_unit`, `currency`, `status`, `contact_email`, `notes`, `updated_at`.
- **Usa:**
  - el listado (`SupplierList`) muestra todos los campos de negocio, incluidas `notes` y `contact_email`;
  - `RateEditor` muestra `updated_at`, el momento de la última tarifa, que el briefing del directorio exige para la trazabilidad de tarifas;
  - `lib/inventory-suppliers.ts` usa `name`, `status` y `categories` para sugerir proveedores al registrar entradas.
- **Por qué no se crea un esquema de listado:** como el listado usa todos los campos, crearlo duplicaría el mismo esquema sin quitar nada.
- **Datos sensibles:** `contact_email` es el correo comercial del proveedor, no una credencial, y el equipo de compras lo necesita.
- **Entradas:**
  - `SupplierCreate`, `RateUpdate` (`rate_per_unit`) y `StatusUpdate` (`status`), todos con `extra="forbid"`;
  - los PATCH solo aceptan el campo que cambian.
- **S4 `DELETE`** devuelve el proveedor eliminado como confirmación.

### 4.7 Inventario (`/inventory`)

**N1–N3 — ✅.**
- **Hoy:** `IngredientRead` = `id`, `name`, `sku`, `unit`, `category`, `country`, `current_stock`. El esquema se construye de forma explícita en `service._to_ingredient_read`, no a partir del ORM.
- **Usa:** `IngredientTable` muestra todos los campos. `IngredientSelect` usa `id`, `name`, `sku` y `unit`. `useIngredientStock` (N3) lee `current_stock` para validar las salidas.
- **Relaciones:** las relaciones ORM `entries` y `exits` del modelo `Ingredient` **no** salen. `current_stock` se calcula a partir de ellas.
- **Entrada:** `IngredientCreate` = `name`, `sku`, `unit`, `category`, `country`, con `extra="forbid"`. No acepta `id` ni `current_stock`, porque el stock solo cambia con órdenes.

**N4 `POST /inventory/orders/inbound`, N5 `POST /inventory/orders/outbound` y N6 `GET /inventory/orders` — ⚠️ anidan el ingrediente junto a su clave foránea.**
- **Hoy:** cada orden es `id`, `ingredient_id`, `quantity`, `location_id`, `created_at`, `user_uuid`, `ingredient{id, name, sku, unit, country}`, más `supplier_name` (entradas) o `reason` (salidas).
- **Usa:**
  - `OrderHistory` (N6): `ingredient.name`, `ingredient.sku`, `ingredient.unit`, `quantity`, `location_id`, `created_at`, `user_uuid` (para marcar "mía"), `supplier_name` y `reason`;
  - `lib/inventory-orders.ts`: `id` y `created_at`, para ordenar y como clave;
  - `EntryForm` y `ExitForm` (N4 y N5): `id`, `quantity`, `ingredient.name`, `ingredient.unit` y `reason`, en el mensaje de confirmación;
  - nadie lee `ingredient_id`, `ingredient.id` ni `ingredient.country`.
- **Por qué cambia:**
  - el mismo identificador sale dos veces (`ingredient_id` e `ingredient.id`), cosa que el briefing señala expresamente ("claves foráneas en bruto cuando hay un objeto anidado disponible");
  - el objeto anidado arrastra `country`, que ninguna pantalla usa;
  - en el historial (N6) eso se repite en cada orden.
- **Objetivo (decisión D4, proyección plana):**
  - `IngredientEntryRead` = `id`, `ingredient_id`, `ingredient_name`, `ingredient_sku`, `ingredient_unit`, `quantity`, `supplier_name`, `location_id`, `created_at`, `user_uuid`;
  - `IngredientExitRead` = `id`, `ingredient_id`, `ingredient_name`, `ingredient_sku`, `ingredient_unit`, `quantity`, `reason`, `location_id`, `created_at`, `user_uuid`;
  - `OrdersRead` = `inbound: list[IngredientEntryRead]`, `outbound: list[IngredientExitRead]`.
- **Relación:** se elige una **proyección plana** con el ID relacionado. Se descartó el objeto anidado completo, porque el cliente no lo necesita, y también el ID solo, porque el historial no carga el catálogo y tendría que cruzar cada orden con él. `ingredient_id` se queda como referencia estable al producto, y ya no hay ningún objeto anidado que lo duplique.
- **`user_uuid`:** se mantiene. Es el identificador del usuario que registró la orden, la UI lo compara con `GET /auth/me` para marcar las órdenes propias, y no es una credencial. El modelo no guarda el nombre ni el email del autor.
- **Entradas:** `IngredientEntryCreate` (`ingredient_id`, `quantity`, `supplier_name`, `location_id`) e `IngredientExitCreate` (`ingredient_id`, `quantity`, `reason`, `location_id`), con `extra="forbid"`. No aceptan `user_uuid` ni `created_at`: el primero sale del token y el segundo lo pone el servidor.
- **Nota:** el historial no tiene paginación (sección 9).

### 4.8 Salud (`/health`)

**H1 `GET /health` — ❌ `dict` sin tipo.**
- **Hoy:** `{"status": "ok"}`, anotado como `dict[str, str]` y sin `response_model`. El contrato en OpenAPI queda como un objeto genérico.
- **Quién la llama:** el `healthcheck` del servicio de la API en `docker-compose.yml`, que solo comprueba el 200, y la supervisión.
- **Objetivo:** `HealthResponse` = `status: Literal["ok"]`. El contenido es el mismo, pero con un contrato explícito. Sigue sin exponer datos internos (versión, dependencias o estado de la base de datos), como fija la propuesta de arquitectura (3.4).

## 5. Decisiones sobre relaciones

| Relación | Endpoints | Decisión | Motivo |
|---|---|---|---|
| Usuario → perfil (1:1) | A2 `GET /auth/me` | **Anidado reducido**: `profile: {name, phone, address}` | El formulario de perfil lo edita como un bloque. Se quitan `id` y `user_id` |
| Usuario → perfil (1:1) | U1 `POST /users` | **No se devuelve** | El cliente acaba de enviar esos datos y no los lee |
| Perfil → usuario | P1–P4 | **No se devuelve `user_id`** | Quien llama ya lo conoce: es él mismo o el valor de la URL |
| Orden → ingrediente (N:1) | N4–N6 | **Proyección plana + ID**: `ingredient_id`, `ingredient_name`, `ingredient_sku`, `ingredient_unit` | Evita duplicar el ID y arrastrar `country`, y no obliga a cruzar con el catálogo |
| Orden → usuario autor | N4–N6 | **Solo el ID** (`user_uuid`) | La UI solo lo compara con la sesión. Los usuarios viven en TinyDB y no se replican en Supabase |
| Ingrediente → órdenes (1:N) | N1–N3 | **No se devuelven**; solo el agregado `current_stock` | El catálogo necesita el stock, no el detalle de las órdenes |

## 6. Plan de implementación

Se hace un commit por subfase. Cada una adapta la API y el backoffice a la vez (decisión D5), actualiza las pruebas y registra el cambio en la sección 7.

| Subfase | Endpoints | Cambio |
|---|---|---|
| 2a | U1, A2, P1–P4 | `UserCreated` en el registro; `ProfileRead` en perfiles y en `/auth/me`; backoffice: tipos `RegisteredUser`, `Profile` y `CurrentUser`, y la `key` de `ProfileForm` |
| 2b | N4–N6 | Órdenes con la proyección plana; backoffice: `OrderBase`, `OrderHistory`, `EntryForm` y `ExitForm` |
| 2c | I4, I2, H1 | `IncidentListItem` en el listado; `response_model=None` explícito en la exportación; `HealthResponse` |
| 2d | Todos | Prueba de guarda: recorre las rutas de la app y falla si alguna `APIRoute` no declara `response_model`, salvo I2 |

Los endpoints ✅ no se tocan. La revisión de proveedores (S1–S6) no encontró nada que cambiar, así que la subfase que el plan reservaba para ellos desaparece.

## 7. Registro de cambios

### 2a — Autenticación, registro y perfiles (U1, A2, P1–P4)

| Endpoint | Antes | Después |
|---|---|---|
| U1 `POST /users` | `UserWithProfile`: `id`, `email`, `is_active`, `role`, `created_at`, `profile{id, user_id, name, phone, address}` | `UserCreated`: `id`, `message` ("Cuenta creada.") |
| A2 `GET /auth/me` | `CurrentUser`: `id`, `email`, `role`, `profile{id, user_id, name, phone, address}` | `CurrentUser`: `id`, `email`, `role`, `profile: ProfileRead \| null` |
| P1–P4 `/profiles/me` y `/profiles/{user_id}` | `Profile`: `id`, `user_id`, `name`, `phone`, `address` | `ProfileRead`: `name`, `phone`, `address` |

**API:**

- `profiles/models.py`:
  - nuevo esquema de salida `ProfileRead`, con los tres atributos nombrados de forma explícita;
  - `Profile` queda como modelo de almacenamiento y gana `to_read()`, la única vía para convertirlo en respuesta.
- `profiles/router.py`: las cuatro rutas declaran `response_model=ProfileRead` y devuelven `to_read()`.
- `users/models.py`: `UserWithProfile` se sustituye por `UserCreated` (`id`, `message`).
- `users/router.py`: `register_user` devuelve `UserCreated`.
- `auth/schemas.py` y `auth/router.py`: `CurrentUser.profile` pasa a ser `ProfileRead | None`, construido con `to_read()`.
- **Entradas:** `UserCreate` y `ProfileUpdate` no cambian. Ya eran esquemas propios, distintos de los de salida, con `extra="forbid"`.

**Backoffice:**

- `types/auth.ts`:
  - `Profile` pierde `id` y `user_id`;
  - `ProfileFields` pasa a ser el mismo tipo;
  - `RegisteredUser` se reduce a `id` y `message`.
- `components/account/AccountProfile.tsx`: la `key` que reinicia el formulario al cambiar de cuenta pasa de `user.profile.id` a `user.id`.
- `RegisterForm` no cambia, porque nunca leía la respuesta del registro.

**Pruebas:**

- Nuevas:
  - REG-F2 comprueba que el registro devuelve exactamente `{id, message}`;
  - las de integración de `/auth/me`, `/profiles/me` y `POST /users` comparan el cuerpo completo, así que cualquier campo de más las hace fallar.
- Adaptadas:
  - las que leían `email` o `profile` de la respuesta del registro ahora lo comprueban en el almacén;
  - las que comprobaban `profile.user_id` ahora comprueban el nombre del perfil leído;
  - `test_me_is_not_taken_as_an_id` comprueba el 200 con el perfil propio.
- Resultados:
  - batería completa de la API: 917 superadas (916 de la línea base + REG-F2);
  - backoffice: `tsc --noEmit` sin errores, Jest 170/170 y lint sin errores.

**Documentación:** los README y los TESTING de la API (en y es) ya describen las respuestas nuevas y el caso REG-F2.

### 2b — Órdenes del inventario (N4–N6)

| Endpoint | Antes | Después |
|---|---|---|
| N4 `POST /inventory/orders/inbound` | `IngredientEntryRead`: `id`, `ingredient_id`, `quantity`, `supplier_name`, `location_id`, `created_at`, `user_uuid`, `ingredient{id, name, sku, unit, country}` | `IngredientEntryRead`: `id`, `ingredient_id`, `ingredient_name`, `ingredient_sku`, `ingredient_unit`, `quantity`, `location_id`, `created_at`, `user_uuid`, `supplier_name` |
| N5 `POST /inventory/orders/outbound` | `IngredientExitRead`: lo mismo, con `reason` en lugar de `supplier_name` | `IngredientExitRead`: la misma proyección plana, con `reason` |
| N6 `GET /inventory/orders` | `OrdersRead` con listas de los dos esquemas anteriores | `OrdersRead` con listas de los dos esquemas nuevos |

**API:**

- `inventory/schemas.py`:
  - desaparece `IngredientSummary`, el objeto anidado;
  - `OrderReadBase` nombra de forma explícita los nueve campos comunes, cada uno con su descripción en OpenAPI;
  - `ingredient_unit` mantiene el tipo `Unit`.
- `inventory/service.py`:
  - `_ingredient_fields` sustituye a `_summary` y añade a cada orden los tres datos del ingrediente;
  - las consultas no cambian: siguen siendo dos `join` en total en `GET /orders`, haya las órdenes que haya;
  - el payload pierde por orden un objeto anidado, el `id` duplicado y el `country` que nadie leía.
- **Entradas:** `IngredientEntryCreate` e `IngredientExitCreate` no cambian. Siguen sin aceptar `user_uuid` ni `created_at`.

**Backoffice:**

- `types/inventory.ts`: `OrderBase` sustituye `ingredient: IngredientSummary` por `ingredient_name`, `ingredient_sku` e `ingredient_unit`, y el tipo `IngredientSummary` desaparece.
- `OrderHistory`, `EntryForm` y `ExitForm` leen los campos planos.
- `lib/inventory-orders.ts` no cambia, porque solo usa `id` y `created_at`.

**Pruebas:**

- Nueva: `test_order_creation_returns_the_flat_projection` compara el cuerpo completo de un `POST /orders/outbound`.
- Adaptadas:
  - `test_orders_list_has_ingredient_data_and_only_schema_fields` exige exactamente los campos planos y que no aparezca `ingredient`;
  - las unitarias de `test_orders.py`, `test_queries.py`, `test_seed.py` y `test_schemas.py` leen `ingredient_sku`, `ingredient_name`, etc.;
  - en Jest, `__tests__/inventory/orders.test.ts` usa la proyección plana.
- Resultados:
  - `tests/inventory` e integración del inventario: 102 superadas (101 + 1 nueva); batería completa de la API: 918;
  - backoffice: `tsc --noEmit` sin errores, Jest 170/170 y lint sin errores.
- **Nota:** Jest no comprueba tipos. La prueba de `orders.test.ts` seguía pasando con el campo antiguo, y fue `tsc` quien lo detectó.

**Documentación:** los README de la API (en y es) describen la forma de las órdenes.

### 2c — Listado de incidencias, `/health` y exportación CSV (I4, H1, I2)

| Endpoint | Antes | Después |
|---|---|---|
| I4 `GET /incidents` | `list[Incident]`: `id`, `title`, `description`, `category`, `status`, `origin`, `branch`, `created_at`, `updated_at` | `list[IncidentListItem]`: los mismos campos sin `updated_at` |
| H1 `GET /health` | Sin `response_model`; `dict[str, str]` | `HealthResponse`: `status: "ok"` |
| I2 `GET /incidents/results/export` | Sin `response_model`; `response_class=Response` | `response_model=None` explícito; OpenAPI documenta `text/csv` con un ejemplo de cabecera. Excepción registrada en `docs/BRIEFING_DIVERGENCES.md` (sección 13) |

**API:**

- `incidents/models.py`:
  - nuevo esquema de salida `IncidentListItem`, con sus ocho atributos nombrados de forma explícita;
  - `Incident` (el detalle) gana `to_list_item()`.
- `incidents/manager_router.py`: `list_incidents` declara `response_model=list[IncidentListItem]` y convierte cada incidencia.
- Los endpoints de alta (I3), detalle (I6) y cambio de estado (I7) siguen devolviendo `Incident`, con `updated_at`.
- `main.py`: `HealthResponse` con `status: Literal["ok"]`. El cuerpo no cambia (`{"status": "ok"}`), así que el healthcheck de `docker-compose.yml` sigue igual.
- `incidents/router.py`: la exportación declara `response_model=None` con un comentario que remite a esta auditoría.

**Backoffice:**

- `types/incident-manager.ts`: nuevo tipo `IncidentListItem`. `Incident` pasa a extenderlo con `updated_at`.
- `lib/gestor-incidencias/api.ts`: `listIncidents` devuelve `IncidentListItem[]`.
- `useIncidents`, `IncidentPanel`, `IncidentList` e `IncidentStatusControl` trabajan con `IncidentListItem`.
- El `PATCH` sigue devolviendo `Incident`, que es un superconjunto, así que sustituir la fila tras cambiar el estado no cambia.

**Pruebas:**

- Nuevas:
  - `test_list_rows_carry_only_the_listing_fields` compara la fila del listado con la incidencia creada sin `updated_at`, y comprueba que el detalle sí lo trae;
  - `test_export_is_documented_as_csv_in_openapi` comprueba que la exportación se publica como `text/csv`.
- Sin cambios: `test_health_stays_public` ya comparaba el cuerpo exacto de `/health`.
- Resultados:
  - suites de incidencias, rutas protegidas y `core`: 326 superadas; batería completa de la API: 920;
  - backoffice: `tsc --noEmit` sin errores, Jest 170/170 y lint sin errores.

**Documentación:**

- README de la API (en y es): filas del listado y de `/health`, y la nota de la exportación.
- `docs/BRIEFING_DIVERGENCES.md`: sección 13, con la excepción del CSV y el destino del PR.

### 2d — Prueba de guarda (todos los endpoints)

Nueva suite `tests/integration/test_response_models.py`. Recorre el esquema OpenAPI de la app real, que es el contrato que ven los clientes, y fija los criterios de esta auditoría para que una ruta nueva o modificada no los rompa sin que nadie se entere:

| Prueba | Qué exige |
|---|---|
| `test_the_app_still_has_the_35_audited_operations` | Que sigan siendo 35 operaciones. Una ruta nueva obliga a auditarla y añadirla a este documento. Desde la captura de telemetría se llama `test_the_app_still_has_the_audited_operations` y espera 36 (sección 11) |
| `test_every_json_response_is_a_named_model_except_the_named_exceptions` | Que toda respuesta 2xx JSON sea un `$ref` a un modelo con nombre, o una lista de ellos. La única excepción es I2 (CSV) |
| `test_the_csv_exception_answers_a_file_not_json` | Que la excepción siga respondiendo `text/csv` |
| `test_no_response_exposes_passwords_hashes_or_reset_tokens` | Que ninguna respuesta, ni siquiera en un modelo anidado, tenga `password`, `hashed_password`, `password_changed_at`, `current_password`, `new_password` ni `token` |
| `test_auth_flows_do_not_echo_the_email_but_me_does` | Que registro, login, forgot/validate/reset y change-password no devuelvan `email`, y que `GET /auth/me` sí lo devuelva |
| `test_writes_do_not_reuse_the_response_schema_as_input` | Que ningún POST, PUT o PATCH use el mismo modelo como entrada y como salida |

**Por qué un modelo con nombre y no solo que "haya `response_model`":**

- FastAPI deduce el modelo de respuesta de la anotación de retorno.
- El antiguo `def health() -> dict[str, str]` tenía, por tanto, un esquema en OpenAPI, pero genérico (`{"type": "object", ...}`) y sin contrato.
- Exigir un `$ref` es lo que distingue un serializer explícito de un `dict`.
- Además, comprobarlo en OpenAPI evita depender de la estructura interna de rutas de FastAPI 0.162, que guarda los routers incluidos en una clase privada (`_IncludedRouter`).

**Comprobación de que la guarda funciona:** se reintrodujeron a propósito, y sin commit, dos regresiones:

- `/health` volvió a `-> dict[str, str]` sin `response_model`;
- `POST /users` pasó a devolver `UserPublic`, con email.

La suite falló con exactamente esas dos rutas (`('GET', '/health')` y `('POST', '/api/v1/users')`). Después se restauraron los dos archivos con `git checkout`.

**Resultado:** las 6 pruebas nuevas pasan; batería completa de la API: 926.

## 8. Verificación

**Línea base** (2026-11-18, antes de cualquier cambio):

- API: `uv run pytest` → 916 pruebas superadas.
- Backoffice: `npx jest` → 170 pruebas superadas (14 suites); `npm run lint` sin errores.

**Resultado final** (2026-11-18, tras la subfase 2d):

| Comprobación | Antes | Después |
|---|---|---|
| `uv run pytest` (API) | 916 superadas | **926 superadas**, ninguna fallida: 10 nuevas (1 en 2a, 1 en 2b, 2 en 2c y 6 de la guarda en 2d) |
| Backoffice `npx jest` | 170 superadas | **170 superadas** |
| Backoffice `npx tsc --noEmit` | sin errores | **sin errores** |
| Backoffice `npm run lint` | sin errores | **sin errores** |
| Backoffice `npm run build` (producción) | — | **compila**, con las 25 rutas |

Por suite, la API pasa de 916 a 926: `tests/auth` sube de 146 a 147 (REG-F2) y `tests/integration` de 325 a 334 (3 de 2b y 2c, y 6 de la guarda). El resto de suites no cambia. Los README y TESTING de la API (en y es) recogen estos recuentos.

**Comparación del OpenAPI.** Se compararon el esquema de antes (generado con `app.openapi()` antes de cualquier cambio) y el de después:

- **Operaciones:** 35 antes y 35 después, sin altas ni bajas.
- **Entradas:** ningún cuerpo de petición cambió.
- **Respuestas 2xx que cambiaron:** las 8 previstas:
  - `POST /users`;
  - las 4 de `/profiles`;
  - `GET /incidents`;
  - `GET /health`;
  - la documentación `text/csv` de la exportación.
- **Esquemas:**
  - añadidos: `HealthResponse`, `IncidentListItem`, `ProfileRead` y `UserCreated`;
  - eliminados: `IngredientSummary`, `Profile` y `UserWithProfile`;
  - modificados: `IngredientEntryRead` e `IngredientExitRead` (`ingredient` → `ingredient_name`, `ingredient_sku` e `ingredient_unit`); `CurrentUser`, cuyo `profile` apunta a `ProfileRead`; e `Incident`, que solo cambia de descripción.
- `GET /auth/me` no aparece entre las respuestas cambiadas porque sigue apuntando a `CurrentUser`. Lo que cambia es ese esquema.
- No hay ningún cambio fuera de lo planificado en la sección 6.

**Prueba manual en `/docs`** (2026-11-18, API local con Supabase; capturas del desarrollador):

| # | Endpoint | Forma comprobada | Resultado |
|---|---|---|---|
| 1 | `POST /api/v1/users` | Registro de la cuenta temporal `serializacion-temp@example.com`: 201 con solo `{id, message}` | ✅ (201 en el log de la API) |
| 2 | `GET /api/v1/auth/me` | `id`, `email` (el propio), `role: "user"` y `profile: {name: "Prueba Serialización", phone: null, address: null}`, sin `id` ni `user_id` en el perfil | ✅ |
| 3 | `GET /api/v1/inventory/orders` | Cada orden con `ingredient_id`, `ingredient_name`, `ingredient_sku`, `ingredient_unit`, `quantity`, `location_id`, `created_at`, `user_uuid` y `supplier_name`/`reason`, sin objeto `ingredient` | ✅ |
| 4 | `GET /health` | `{"status": "ok"}` | ✅ |
| 5 | `GET /api/v1/incidents` | Filas con `id`, `title`, `description`, `category`, `status`, `origin`, `branch` y `created_at`, sin `updated_at` | ✅ |

La cuenta temporal se borró al terminar con `DELETE /api/v1/users/{id}` (200). Después no queda rastro de su email ni de su `id` en `storage/auth-db.json`. Un segundo `DELETE` con el mismo token respondió 401, porque el token de una cuenta borrada deja de valer.

## 9. Fuera de alcance y mejoras futuras

- **Paginación** de `GET /incidents` y `GET /inventory/orders`: los dos devuelven la colección completa. Con usuarios reales y más volumen convendrá añadir `limit`/`offset` o un cursor. Cambia el contrato de consulta y no la forma de cada elemento, así que no forma parte de esta auditoría.
- **Herramienta de talento** (`lib/talento/api.ts`): consume una API externa, no `brasaland-api`.

## 10. Criterios de evaluación

| Criterio del briefing | Cumplimiento | Evidencia |
|---|---|---|
| Cada endpoint tiene un `response_model` explícito declarado | ✅ | 34 de 35 con un modelo con nombre; la exportación CSV declara `response_model=None` como excepción documentada (4.4, I2; `BRIEFING_DIVERGENCES.md`, sección 13). Lo impone `test_every_json_response_is_a_named_model_except_the_named_exceptions` |
| Esquemas de entrada y salida definidos y sin confundirse | ✅ | Cada escritura tiene su `*Create`/`*Update`/`StatusUpdate` con `extra="forbid"` (sección 4); `test_writes_do_not_reuse_the_response_schema_as_input` lo comprueba sobre OpenAPI |
| Los listados devuelven solo lo necesario, sin anidado ni over-fetching | ✅ | `IncidentListItem` (I4); órdenes con proyección plana (N4–N6); los listados de proveedores y productos ya devolvían solo campos usados (4.6, 4.7); relaciones en la sección 5 |
| Ninguna respuesta expone contraseñas hasheadas ni tokens internos; los flujos de auth no autenticados no reenvían el email; `/auth/me` sí puede | ✅ | Registro → `{id, message}` (U1); login y forgot/validate/reset sin email (4.1); `test_no_response_exposes_passwords_hashes_or_reset_tokens` y `test_auth_flows_do_not_echo_the_email_but_me_does` |
| `docs/serialization-audit.md` lista todos los endpoints, su estado original y los cambios | ✅ | Tabla general con estado original y final (sección 3), fichas (4), registro de cambios por subfase (7) |
| La aplicación sigue funcionando sin regresiones | ✅ | 926 pruebas de la API, Jest 170, `tsc`, lint y build del backoffice; OpenAPI sin cambios fuera de lo previsto; prueba manual en `/docs` (sección 8) |

## 11. Rutas añadidas después de la auditoría

Las rutas nuevas se auditan con los mismos criterios antes de ampliar el recuento de la guarda (`test_the_app_still_has_the_audited_operations`).

| # | Operación | Para qué | Entrada | Salida | Consumidor | Estado |
|---|---|---|---|---|---|---|
| T1 | `POST /telemetry/events` (captura de telemetría, 2026-11-19) | Receptor provisional de los lotes de telemetría del backoffice | `TelemetryBatch` (`events`: 1–100 `TelemetryEvent`), `extra="forbid"` | `TelemetryReceipt`: `received` | `lib/telemetry/` del backoffice (`fetch` y `sendBeacon`) | ✅ |
| T2 | `GET /telemetry/report` (reporte técnico, 2026-11-20) | Métricas técnicas por día calculadas sobre `telemetry_events` | Query `start_date` y `end_date` opcionales (ISO 8601); sin cuerpo | `TelemetryReport`: `period` (`ReportPeriod`) y `metrics` (`ReportMetrics`: listas de `EventsPerDay`, `ErrorRateByType`, `ApiLatencyByRoute` y `AuthFailureRate`) | Vista `/telemetria` del backoffice, por su intermediario | Retirada (#DEV-55, Q1) |
| T3 | `GET /api/v1/locations` (catálogo de locales, 2026-11-20) | Los 14 locales con su sede, ciudad, país y moneda (tabla `locations`, migración 004) | Sin parámetros ni cuerpo | Lista de `LocationRead`: `id`, `code`, `name`, `city`, `country` y `currency` | Formularios del inventario del backoffice, por su intermediario | ✅ |
| R1 | `GET /reporting/weekly-location-performance` (pipeline de desempeño de negocio, 2026-11-23) | Las filas de KPIs de una semana: el Reporte Semanal de Costo y Merma por Local | Query `week_start` opcional (un lunes); sin cuerpo | `WeeklyLocationPerformance`: `week_start` y lista de `LocationWeekPerformance` (`location_id`, `location_name`, `country`, los cinco KPIs y `currency`) | Dashboard de la Parte 3 | ✅ |
| R2 | `GET /reporting/pipeline-runs/latest` (ídem) | Estado y metadata de la última corrida del pipeline (`reporting.pipeline_runs`) | Sin parámetros ni cuerpo | `PipelineRunRead`: id, disparo, estado, rango de semanas, horas, conteos, `issues`, filas escritas y error | Dashboard de la Parte 3; seguimiento de una corrida manual | ✅ |
| R3 | `POST /reporting/pipeline-runs` (ídem) | Pide a Prefect una corrida manual, sin esperar (202) | `PipelineRunRequest`: `week_from` y `week_to` opcionales, `extra="forbid"`; cuerpo opcional | `PipelineRunRead` de la corrida en `pending` | Administradores (dashboard de la Parte 3) | ✅ |
| Q1 | `POST /telemetry/report` (cola de tareas, #DEV-55, 2026-11-25) | Encola el reporte técnico (tarea `telemetry.report`) y responde `202` al momento; sustituye a T2 | `TelemetryReportRequest`: `start_date` y `end_date` opcionales (ISO 8601), `extra="forbid"`; cuerpo opcional | `TaskAccepted`: `task_id` (y la cabecera `Location`) | Vista `/telemetria` del backoffice, por su intermediario | ✅ |
| Q2 | `GET /tasks/{task_id}` (ídem) | Estado de una tarea encolada y su resultado cuando termina | Path `task_id` (UUID); sin cuerpo | `TaskStatus`: `task_id`, `status` (`pending`, `started`, `success` o `failure`) y `result` | Vista `/telemetria` del backoffice, que la consulta cada 1–2 s | ✅ |

**T1.** La salida es un modelo con nombre y solo dice cuántos eventos llegaron: no devuelve los eventos ni ningún dato del usuario. La entrada es un esquema propio, distinto de la salida. La ruta es pública y está fuera de `/api/v1` (plan de telemetría, sección 13.3), así que figura entre las rutas públicas de `test_protected_routes.py`. Con ella, la aplicación tiene **36 operaciones**.

**Cambio posterior en T1 (almacenamiento de telemetría, 2026-11-19).** La entrada pasa a ser laxa: `TelemetryBatch.events` es una lista de elementos sin validar (`list[Any]`), porque cada evento se valida después por separado con `TelemetryEvent.model_validate` y un evento inválido no puede hacer fallar el lote (plan de telemetría, sección 14.3). El esquema sigue siendo propio y distinto de la salida. La salida, `TelemetryReceipt`, pasa a `received`, `stored` y `rejected`: siguen siendo solo cantidades, sin eventos ni datos del usuario. El recuento de operaciones no cambia (36).

**T2.** La salida es un modelo con nombre, y cada métrica tiene su propio modelo de fila. Solo lleva agregados por día (recuentos, tasas y latencias por plantilla de ruta): ningún evento, `user_id`, `session_id` ni dato de la cuenta. No tiene cuerpo de entrada. Como el inventario, la respuesta se envía ya serializada desde la cache (`X-Cache`), y el `response_model` documenta el contrato: el JSON sale de `TelemetryReport.model_dump_json`, así que no puede apartarse de él. La ruta exige token y rol `admin` (plan de telemetría, sección 16.3), así que no figura entre las rutas públicas de `test_protected_routes.py`. Con ella, la aplicación tiene **37 operaciones**.

**T3.** La salida es una lista de un modelo con nombre, independiente del modelo ORM `Location`, y solo describe locales: ningún dato de personas. No tiene entrada. Como el inventario, la respuesta se envía ya serializada desde la cache (`X-Cache`, 10 minutos) y el `response_model` documenta el contrato. La ruta exige token, como el resto de `/api/v1`, así que no figura entre las rutas públicas de `test_protected_routes.py`. Con ella, la aplicación tiene **38 operaciones**.

**R1–R3.** Las tres salidas son modelos con nombre propios del paquete `services/reporting` (`brasaland_reporting.schemas`), independientes de las tablas de `data/pipelines`. Solo llevan agregados de negocio por local y semana y metadata de las corridas: ningún evento, `user_id` ni dato de una cuenta. `PipelineRunRead` deja fuera `requested_by` (quién pidió la corrida) y `prefect_flow_run_id`, que solo sirven para auditar en la base. La única entrada, `PipelineRunRequest`, es un esquema propio, distinto de la salida, y rechaza claves desconocidas. Como el inventario, R1 se envía ya serializado desde la cache (`X-Cache`, 5 minutos) y su `response_model` documenta el contrato. Las tres exigen token (lecturas para `admin` y `manager`, disparo solo `admin`) y están fuera de `/api/v1`, como las de telemetría; no figuran entre las rutas públicas de `test_protected_routes.py`. Con ellas, la aplicación tiene **41 operaciones**.

**Q1–Q2 (cola de tareas, ticket #DEV-55).** El informe técnico deja de calcularse en la petición: Q1 sustituye a T2 (mismo path, ahora `POST`, porque crea trabajo) y Q2 es nueva. Las dos salidas son modelos con nombre del dominio `tasks`. `TaskAccepted` solo lleva el id. `TaskStatus` lleva los tres campos del ticket; `result` es abierto (`Any`) porque la ruta sirve para cualquier tarea: con `success` es el informe, cuya forma sigue siendo `TelemetryReport` (los modelos de T2 se conservan como contrato, y `tests/telemetry/test_report_task_contract.py` valida con ellos el informe que arma el worker); con `failure`, `{"error"}` con el tipo y la primera línea del error, sin SQL ni traceback (el error completo queda en el log del worker y en `ops.task_dead_letters`). Ninguna de las dos expone quién encoló la tarea ni sus argumentos. La entrada de Q1, `TelemetryReportRequest`, es un esquema propio, distinto de la salida, y rechaza claves desconocidas. Q1 exige rol `admin` y Q2 token, y solo responde a quien encoló la tarea o a un admin (404 para cualquier otro); las dos están fuera de `/api/v1` y no figuran entre las rutas públicas de `test_protected_routes.py`. Sin T2 y con ellas, la aplicación tiene **42 operaciones**.

**Cambio posterior en I4 (`GET /incidents`, captura de telemetría, 2026-11-19).** `IncidentListItem` vuelve a incluir `updated_at`. La auditoría lo quitó porque ninguna pantalla lo leía; ahora el gestor lo usa para calcular `minutes_in_previous_status` del evento `incident_status_changed` sin pedir el detalle de cada incidencia. El listado sigue sin anidar nada y con un modelo propio, distinto del de entrada. `test_list_rows_carry_only_the_listing_fields` compara ahora la fila con la incidencia creada completa.
