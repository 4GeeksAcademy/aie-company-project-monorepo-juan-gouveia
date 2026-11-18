# Auditoría de serialización — Brasaland API

Esta auditoría revisa todos los endpoints de `services/brasaland-api` (FastAPI) antes de que la API reciba usuarios reales. Para cada endpoint registra:

- qué recibe;
- qué devuelve hoy;
- qué lee de verdad su consumidor;
- qué debería devolver.

La clasificación de partida se conserva. Después se registran los cambios aplicados y la verificación.

- **Rama:** `feature/serialization-audit`.
- **Fecha de la auditoría inicial:** 2026-11-18.
- **Estado:** Fase 1 completada (auditoría). La implementación (Fase 2) y la verificación (Fase 3) se registran en las secciones 7 y 8 a medida que avanzan.

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

**Leyenda:**

- **Auth:** `—` = pública; `JWT` = requiere token; `admin` = solo administradores.
- **Consumidor:** el archivo del backoffice que llama a la ruta. "API" significa que no hay pantalla que la use (clientes de la API, administración o pruebas).

| # | Método y ruta | Propósito | Auth | Entrada | `response_model` actual | Consumidor | Estado original |
|---|---|---|---|---|---|---|---|
| A1 | `POST /api/v1/auth/login` | Iniciar sesión | — | `LoginRequest` | `Token` | `lib/auth/api.ts` | ✅ |
| A2 | `GET /api/v1/auth/me` | Usuario de la sesión y su perfil | JWT | — | `CurrentUser` | `AccountMenu`, `AccountProfile`, `OrdersPanel` | ⚠️ |
| A3 | `POST /api/v1/auth/forgot-password` | Pedir el enlace de restablecimiento | — | `ForgotPasswordRequest` | `MessageResponse` | `lib/auth/api.ts` | ✅ |
| A4 | `POST /api/v1/auth/reset-password/validate` | Validar el enlace antes de pintar el formulario | — | `ResetTokenCheck` | `MessageResponse` | `lib/auth/api.ts` | ✅ |
| A5 | `POST /api/v1/auth/reset-password` | Fijar una contraseña nueva con el enlace | — | `ResetPasswordRequest` | `MessageResponse` | `lib/auth/api.ts` | ✅ |
| A6 | `POST /api/v1/auth/change-password` | Cambiar la contraseña con la sesión iniciada | JWT | `ChangePasswordRequest` | `PasswordChanged` | `ChangePasswordForm` | ✅ |
| U1 | `POST /api/v1/users` | Registro | — | `UserCreate` | `UserWithProfile` | `RegisterForm` | ⚠️ |
| U2 | `GET /api/v1/users` | Listar cuentas | admin | — | `list[UserPublic]` | API | ✅ |
| U3 | `GET /api/v1/users/{user_id}` | Ver una cuenta | JWT (propia o admin) | — | `UserPublic` | API | ✅ |
| U4 | `PUT /api/v1/users/{user_id}` | Cambiar credenciales, rol o estado | JWT (propia o admin) | `UserUpdate` | `UserPublic` | API | ✅ |
| U5 | `DELETE /api/v1/users/{user_id}` | Borrar una cuenta y su perfil | JWT (propia o admin) | — | `UserPublic` | API | ✅ |
| P1 | `GET /api/v1/profiles/me` | Perfil propio | JWT | — | `Profile` | API | ⚠️ |
| P2 | `PUT /api/v1/profiles/me` | Editar el perfil propio | JWT | `ProfileUpdate` | `Profile` | `ProfileForm` | ⚠️ |
| P3 | `GET /api/v1/profiles/{user_id}` | Perfil de una cuenta | JWT (propio o admin) | — | `Profile` | API | ⚠️ |
| P4 | `PUT /api/v1/profiles/{user_id}` | Editar un perfil por usuario | JWT (dueño) | `ProfileUpdate` | `Profile` | API | ⚠️ |
| I1 | `POST /api/v1/incidents/analyze` | Analizar el CSV de incidentes | JWT | `multipart` (`file`) | `AnalysisResponse` | `IncidentAnalysisPanel` y subcomponentes | ✅ |
| I2 | `GET /api/v1/incidents/results/export` | Descargar `results.csv` | JWT | — | ninguno (`response_class=Response`, `text/csv`) | `lib/incidencias/api.ts` | Excepción |
| I3 | `POST /api/v1/incidents` | Registrar una incidencia | JWT | `IncidentCreate` | `Incident` | `IncidentForm` | ✅ |
| I4 | `GET /api/v1/incidents` | Listar incidencias con filtros | JWT | query `status`, `origin`, `branch`, `category` | `list[Incident]` | `IncidentList` | ⚠️ |
| I5 | `GET /api/v1/incidents/summary` | Métricas del gestor | JWT | — | `IncidentSummary` | `IncidentSummaryPanel` | ✅ |
| I6 | `GET /api/v1/incidents/{incident_id}` | Detalle de una incidencia | JWT | — | `Incident` | API | ✅ |
| I7 | `PATCH /api/v1/incidents/{incident_id}/status` | Cambiar el estado | JWT | `StatusUpdate` | `Incident` | `IncidentStatusControl` | ✅ |
| S1 | `POST /api/v1/suppliers` | Alta de proveedor | JWT | `SupplierCreate` | `Supplier` | `SupplierFormModal` | ✅ |
| S2 | `GET /api/v1/suppliers` | Directorio con filtros | JWT | query `country`, `category` | `list[Supplier]` | `SupplierList`, `lib/inventory-suppliers.ts` | ✅ |
| S3 | `GET /api/v1/suppliers/{supplier_id}` | Detalle de un proveedor | JWT | — | `Supplier` | API | ✅ |
| S4 | `DELETE /api/v1/suppliers/{supplier_id}` | Borrar un proveedor | JWT | — | `Supplier` | API | ✅ |
| S5 | `PATCH /api/v1/suppliers/{supplier_id}/rate` | Actualizar la tarifa | JWT | `RateUpdate` | `Supplier` | `RateEditor` | ✅ |
| S6 | `PATCH /api/v1/suppliers/{supplier_id}/status` | Activar o suspender | JWT | `StatusUpdate` | `Supplier` | `StatusToggle` | ✅ |
| N1 | `GET /api/v1/inventory/products` | Catálogo con stock calculado | JWT | query `country` | `list[IngredientRead]` | `IngredientTable`, `IngredientSelect` | ✅ |
| N2 | `POST /api/v1/inventory/products` | Alta de ingrediente | JWT | `IngredientCreate` | `IngredientRead` | API | ✅ |
| N3 | `GET /api/v1/inventory/products/{ingredient_id}` | Stock de un ingrediente | JWT | — | `IngredientRead` | `useIngredientStock` | ✅ |
| N4 | `POST /api/v1/inventory/orders/inbound` | Registrar una entrada | JWT | `IngredientEntryCreate` | `IngredientEntryRead` | `EntryForm` | ⚠️ |
| N5 | `POST /api/v1/inventory/orders/outbound` | Registrar una salida | JWT | `IngredientExitCreate` | `IngredientExitRead` | `ExitForm` | ⚠️ |
| N6 | `GET /api/v1/inventory/orders` | Historial de entradas y salidas | JWT | — | `OrdersRead` | `OrderHistory` | ⚠️ |
| H1 | `GET /health` | Comprobación de vida | — | — | ninguno (`dict[str, str]`) | Docker / supervisión | ❌ |

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

## 8. Verificación

**Línea base** (2026-11-18, antes de cualquier cambio):

- API: `uv run pytest` → 916 pruebas superadas.
- Backoffice: `npx jest` → 170 pruebas superadas (14 suites); `npm run lint` sin errores.

_El resultado final, la comparación del OpenAPI y las pruebas manuales en `/docs` se completan en la Fase 3._

## 9. Fuera de alcance y mejoras futuras

- **Paginación** de `GET /incidents` y `GET /inventory/orders`: los dos devuelven la colección completa. Con usuarios reales y más volumen convendrá añadir `limit`/`offset` o un cursor. Cambia el contrato de consulta y no la forma de cada elemento, así que no forma parte de esta auditoría.
- **Herramienta de talento** (`lib/talento/api.ts`): consume una API externa, no `brasaland-api`.
