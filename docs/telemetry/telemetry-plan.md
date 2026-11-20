# Plan de Telemetría — Brasaland

Respuesta técnica al RFI del equipo de gestión: qué datos vale la pena capturar hoy en la plataforma de Brasaland (API `services/brasaland-api` y backoffice `uis/backoffice`), y cuáles serán valiosos mañana, **antes de escribir una sola línea de instrumentación**. El plan está pensado para que otro desarrollador lo implemente sin tener que preguntar nada.

- **Entregables:** este documento y [`event-schemas.json`](event-schemas.json) (los esquemas de cada evento).
- **Fuentes:** el briefing de Brasaland (métricas obligatorias, entidades y restricciones), el enunciado del RFI y el código actual del monorepo.
- **Estado:** aprobado, con las revisiones de las fases de captura, almacenamiento y reporte técnico (catálogo 1.2.0 de los esquemas). Incluye el catálogo, el envelope, los datos sensibles, la estrategia de entrega, los riesgos y exclusiones, las brechas con el modelo actual, la fase de captura en el backoffice, la fase de almacenamiento, una ficha por cada uno de los 44 eventos y la fase de reporte técnico.
- **Fase de captura:** implementada y verificada (2026-11-19). 34 de los 44 eventos se emiten desde el backoffice con una única función `track()`, al recibir la respuesta de la API que confirma o rechaza cada hecho; la sección 13.6 dice dónde se captura cada uno. Los 10 restantes esperan al emisor de la API (sección 13).
- **Fase de almacenamiento:** el receptor guarda los eventos válidos en la tabla `telemetry_events` de Supabase y rechaza los demás uno a uno (sección 14).
- **Fase de reporte técnico:** un pipeline en Python con Pandas calcula métricas operacionales por día sobre `telemetry_events`, y `GET /telemetry/report` las sirve con una cache de 60 s (sección 16).

## Índice

1. [Propósito y alcance](#1-propósito-y-alcance)
2. [Método y convenciones](#2-método-y-convenciones)
3. [Métricas obligatorias](#3-métricas-obligatorias)
4. [Flujo de gestión de inventario](#4-flujo-de-gestión-de-inventario)
5. [Catálogo de oportunidades identificadas](#5-catálogo-de-oportunidades-identificadas)
6. [Resumen del catálogo](#6-resumen-del-catálogo)
7. [Event Envelope](#7-event-envelope)
8. [Datos sensibles y PII](#8-datos-sensibles-y-pii)
9. [Estrategia de entrega: stream o batch](#9-estrategia-de-entrega-stream-o-batch)
10. [Throttle y debounce](#10-throttle-y-debounce)
11. [Riesgos y exclusiones](#11-riesgos-y-exclusiones)
12. [Brechas de instrumentación](#12-brechas-de-instrumentación)
13. [Fase de captura en el backoffice](#13-fase-de-captura-en-el-backoffice)
14. [Fase de almacenamiento](#14-fase-de-almacenamiento)
15. [Fichas de los eventos](#15-fichas-de-los-eventos)
16. [Fase de reporte técnico](#16-fase-de-reporte-técnico)

## 1. Propósito y alcance

El sistema de inventario de Brasaland ya está en producción: FastAPI con autenticación JWT, modelo relacional en Supabase y una regla innegociable: **el stock no se modifica directamente, solo con órdenes de entrada y salida trazables a un usuario**. Funciona, pero nadie sabe qué pasa dentro de él. Hoy no se puede responder a ninguna de estas preguntas del equipo de operaciones:

- ¿Cuántas órdenes de salida se registran por día?
- ¿Qué productos acumulan más errores de validación?
- ¿Hay usuarios intentando modificar el stock directamente y siendo rechazados?
- ¿Cuándo se disparan más las alertas de stock mínimo?
- ¿Cuántos intentos de login fallidos hay por día?
- ¿Qué secciones visitan más los operadores?
- ¿Qué flujos se abandonan a la mitad?

**Alcance:** el inventario es el núcleo, porque de él salen las métricas obligatorias. El catálogo cubre además **todo lo que un humano o un proceso toca** en la plataforma:

| Área | Qué incluye |
|---|---|
| Autenticación y sesión | Login, registro, recuperación y cambio de contraseña, expiración y revocación de sesiones, cambios de acceso |
| Navegación | Vistas visitadas, formularios abandonados, filtros y listas largas del backoffice |
| Rendimiento | Latencia de la API, carga de las páginas, eficacia de la caché |
| Errores | Errores de la API, errores 500, errores de frontend no capturados, caídas de conexión, correos no entregados |
| Otras áreas del negocio | Directorio de proveedores, gestor de incidencias y analizador del CSV de incidentes |
| Procesos internos | Arranque de la API y cargas de datos por scripts |

**Fuera de alcance de este documento:** el código de instrumentación, el pipeline y el almacenamiento. Son las fases siguientes de la serie. El plan sí deja decidido qué se captura, con qué forma y con qué urgencia.

## 2. Método y convenciones

### 2.1 La regla de oro

Un evento solo existe si se puede completar esta frase:

> *"Capturamos `[event_type]` porque necesitamos saber `[hipótesis]`, lo que nos permite tomar la decisión `[decisión concreta]`."*

Cada evento del catálogo lleva su frase completa y la persona o el equipo que toma esa decisión. Lo que no supera la frase no entra en el catálogo: va a la sección 11 (riesgos y exclusiones), con su motivo.

### 2.2 Clasificación

- **Obligatorio:** viene del briefing de Brasaland (sección 3). Su `event_type`, sus entidades y sus propiedades mínimas coinciden exactamente con el briefing.
- **Oportunidad identificada:** la propone este plan (sección 5) a partir del recorrido del código y de las preguntas del RFI.

### 2.3 Taxonomía de `event_type`

Todos los nombres siguen el formato `entidad_acción`, en snake_case, con la acción en **participio pasado**: el evento describe algo que ya ocurrió.

| Verbo | Significado | Ejemplos |
|---|---|---|
| `created` | Se creó una entidad | `inbound_order_created`, `incident_created` |
| `registered` | Se dio de alta algo que ya existía fuera del sistema | `stock_waste_registered`, `user_registered` |
| `updated` / `changed` | Cambió un valor, o el estado de un ciclo de vida | `supplier_rate_updated`, `incident_status_changed` |
| `rejected` | El sistema rechazó la operación por una regla | `direct_stock_edit_rejected`, `outbound_order_rejected` |
| `failed` | La operación falló por un error del usuario o del sistema | `login_failed`, `order_validation_failed` |
| `succeeded` / `completed` | La operación terminó bien | `login_succeeded`, `password_reset_completed` |
| `triggered` / `detected` | El sistema detectó una condición | `stock_threshold_triggered`, `ingredient_price_variance_detected` |
| `viewed` / `applied` / `extended` / `abandoned` | Acción de navegación en el backoffice | `page_viewed`, `list_filter_applied`, `form_abandoned` |
| `recorded` / `captured` | Medición técnica | `api_latency_recorded`, `frontend_error_captured` |
| `requested` / `returned` / `occurred` / `started` / `executed` / `analyzed` / `exported` / `deleted` / `expired` | Otros hechos puntuales | `password_reset_requested`, `api_error_returned`, `server_error_occurred`, `api_instance_started`, `data_seed_executed`, `incident_report_analyzed`, `supplier_deleted`, `session_expired` |

### 2.4 Emisores

Cada evento tiene un solo emisor. Así un hecho no se cuenta dos veces y está claro quién lo instrumenta.

| Emisor | Dónde | Para qué |
|---|---|---|
| **API** | `services/brasaland-api` | Hechos de negocio confirmados (después del `commit`), rechazos de reglas, autenticación, errores y latencia. Es la fuente de verdad: lo que pasa por la API ocurre, lo vea o no el navegador. |
| **BFF** | Intermediario `app/api/[...path]/route.ts` del backoffice | Fallos de conexión entre el backoffice y la API |
| **Navegador** | Backoffice (React) | Lo que solo existe en la interfaz: vistas, formularios abandonados, filtros, rendimiento de carga y errores de JavaScript |
| **Proceso** | Arranque de la API y scripts de `scripts/` y `uv run …` | Actividad que no nace de una petición HTTP |

**Regla de emisión de la API:** los eventos de negocio se emiten **después del `commit`**. Una operación que se revierte no deja eventos de éxito.

**Emisor en la fase de captura.** La primera implementación captura los eventos en el backoffice, con una única función `track()` (sección 13). Por eso, 26 eventos que esta tabla asignaba a la API o al BFF pasan al **navegador** (`source: "browser"`). Se emiten **al recibir la respuesta de la API**: un 2xx confirma que la operación ya está guardada (después del `commit`), y un rechazo trae su código de error, así que la regla anterior se mantiene. Los 7 eventos que solo puede emitir la API y los 3 de procesos esperan al emisor del servidor. Cada evento sigue teniendo un único emisor.

### 2.5 Nombres del briefing frente al modelo actual

Las métricas obligatorias usan las entidades del briefing (`Product`, `InboundOrder`, `OutboundOrder`, `location`, `supplier`). El código del inventario (Hito 5) usa `Ingredient`, `IngredientEntry` e `IngredientExit`. **Los eventos y sus propiedades usan siempre los nombres del briefing**, como `product_id` y `product_category`. La correspondencia con el modelo, y los cambios que necesita el modelo para emitir cada evento, están en la sección 12 (brechas de instrumentación).

### 2.6 Responsables de las decisiones

| Persona o equipo | Área | Decisiones que alimenta |
|---|---|---|
| Felipe Guerrero | Operaciones de Restaurante | Reabastecimiento, mínimos, mermas, disciplina operativa por local |
| Lucía Fernández | Compras y Proveedores | Consolidación de compras, precios, proveedores |
| Jake Morrison | Formación y Estándares de Calidad | Capacitación del personal, uso correcto del sistema |
| Mariana Restrepo | Dirección Ejecutiva | Alertas estratégicas (precios, pérdidas) |
| Nicolás Park (equipo de Tecnología) | Tecnología | Salud técnica, seguridad, rendimiento, UX del backoffice |

## 3. Métricas obligatorias

Las 6 métricas del briefing son el **piso** del plan. Se instrumentan de punta a punta (captura → almacenamiento) a lo largo de la serie, y están pensadas para agregarse por local, por país y por semana. En la fase de captura las emite el backoffice al recibir la respuesta de la API (§2.4 y sección 13).

| `event_type` | Se dispara cuando… (briefing) | Emisor | Disparo preciso en la plataforma | Responsable |
|---|---|---|---|---|
| `inbound_order_created` | Un local registra la llegada de mercancía de un proveedor | Navegador | Al recibir el 201 de `POST /api/v1/inventory/orders/inbound` (la entrada ya está guardada) | Lucía |
| `outbound_order_created` | Un local registra consumo de ingredientes en la preparación de un plato | Navegador | Al recibir el 201 de `POST /api/v1/inventory/orders/outbound` con motivo de **consumo** | Felipe |
| `stock_waste_registered` | Un local registra merma (producto vencido, error de cocina, o pérdida/robo) | Navegador | Al recibir el 201 de `POST /api/v1/inventory/orders/outbound` con motivo de **merma** | Felipe |
| `stock_threshold_triggered` | El stock de un producto cae por debajo del mínimo configurado para ese local | Navegador | Al recibir el 201 de una salida que hace que el stock **cruce** el mínimo: antes ≥ mínimo y después < mínimo | Felipe |
| `direct_stock_edit_rejected` | Un usuario intenta modificar el stock directamente (fuera de una orden) y el sistema lo rechaza | Navegador | Al recibir el rechazo de la API a un intento de edición directa (definición en §3.2) | Jake |
| `ingredient_price_variance_detected` | El costo unitario de una orden de entrada varía más de un umbral (ej. 10%) respecto al histórico del mismo producto/proveedor | Navegador | Al recibir el 201 de una entrada cuyo coste unitario se desvía más del 10 % de la media histórica del mismo producto y proveedor | Lucía y Mariana |

### 3.1 La regla de oro de cada métrica obligatoria

Las hipótesis y las decisiones son las del briefing.

- **`inbound_order_created`:** *"Capturamos `inbound_order_created` porque necesitamos saber cuánto y qué se está comprando, por local y por proveedor, lo que nos permite tomar la decisión de consolidar compras entre locales para negociar mejores precios."* — Lucía.
- **`outbound_order_created`:** *"Capturamos `outbound_order_created` porque necesitamos saber qué ingredientes se consumen más, y a qué ritmo, por local, lo que nos permite tomar la decisión de ajustar la sugerencia automática de pedidos a proveedores."* — Felipe.
- **`stock_waste_registered`:** *"Capturamos `stock_waste_registered` porque necesitamos saber cuánto producto se pierde, por qué razón, y en qué local, lo que nos permite tomar la decisión de priorizar auditorías de merma en los locales con peor indicador."* — Felipe.
- **`stock_threshold_triggered`:** *"Capturamos `stock_threshold_triggered` porque necesitamos saber con qué frecuencia un local se queda corto de un ingrediente clave, lo que nos permite tomar la decisión de ajustar el umbral mínimo o la frecuencia de reabastecimiento de ese producto."* — Felipe.
- **`direct_stock_edit_rejected`:** *"Capturamos `direct_stock_edit_rejected` porque necesitamos saber si el personal está intentando saltarse el control de trazabilidad, lo que nos permite tomar la decisión de reforzar capacitación o permisos en los locales donde esto ocurre con más frecuencia."* — Jake.
- **`ingredient_price_variance_detected`:** *"Capturamos `ingredient_price_variance_detected` porque necesitamos saber cuándo un ingrediente clave (ej. carne) sube de precio de forma anómala, lo que nos permite tomar la decisión de alertar a Lucía y a Mariana para renegociar o buscar proveedor alterno."* — Lucía y Mariana.

**Propiedades mínimas** de estos eventos, además del envelope (briefing): `location_id`, `country` (`CO`/`US`), `product_id`, `product_category`, `quantity`, `unit` y `currency` (`COP`/`USD`). `stock_waste_registered` lleva además `reason` (`expired`, `kitchen_error`, `theft_suspected`). Ningún evento lleva nombres de empleados ni datos de clientes. Los importes van en la moneda del local, sin conversión.

### 3.2 Decisiones de interpretación

- **Una salida emite un único evento, según su motivo.** El briefing describe `outbound_order_created` como consumo "en la preparación de un plato" y `stock_waste_registered` como merma, y reserva `reason` para la merma. Por eso, una salida de consumo emite `outbound_order_created` y una de merma emite `stock_waste_registered`, nunca los dos. Así la merma no se cuenta también como consumo, y el total de órdenes de salida por día es la suma de ambos eventos.
- **`stock_threshold_triggered` se emite al cruzar el mínimo, no en cada salida por debajo de él.** Una alerta repetida en cada consumo de un producto ya bajo no aporta nada nuevo y taparía las alertas nuevas. Si el stock se repone por encima del mínimo y vuelve a caer, se emite otra vez. **Mínimo en la fase de captura:** mientras no existan mínimos por local (brecha B3), se usa el umbral de stock bajo que ya muestra el backoffice para la unidad del producto (`LOW_STOCK_THRESHOLDS`: 40 kg, 25 litros, 100 unidades), sobre el stock global del producto.
- **Qué es un "intento de edición directa"** (`direct_stock_edit_rejected`). El sistema no ofrece ninguna forma de editar el stock, así que el intento se reconoce por cómo lo rechaza la API:
  1. `PUT`, `PATCH` o `DELETE` sobre `/api/v1/inventory/products/{id}` o sobre las rutas de órdenes: hoy responde **405** (`http_405`);
  2. un cuerpo de `POST /inventory/products`, `/orders/inbound` u `/orders/outbound` que incluya `current_stock` o `stock`: hoy responde **422** (`invalid_request`, error `extra_forbidden` en ese campo).

  Ambos casos requieren un usuario autenticado. Sin token, la API responde 401 antes de llegar a la ruta, y ese caso lo cubre la autenticación. Fuera de la interfaz, estos intentos llegan de scripts, Postman o `curl`, y los verá el emisor de la API. **En la fase de captura**, el backoffice ofrece en `/inventario/ingredientes` la acción "Ajustar stock": envía el `PATCH` real con `current_stock`, la API lo rechaza con 405 y la interfaz explica que el stock solo cambia con órdenes. Así se mide justo lo que quiere detectar el briefing: personal que intenta saltarse la trazabilidad desde la herramienta que usa.
- **`ingredient_price_variance_detected` compara con la media histórica del mismo producto y proveedor.** Se usan las entradas de los últimos 90 días, con un mínimo de 3 entradas para considerar que hay histórico, y un umbral del **10 %**, el ejemplo del briefing, configurable. Si no hay histórico suficiente, no se emite: una primera compra no es una anomalía. En la fase de captura, el backoffice calcula la media con el historial de `GET /api/v1/inventory/orders`.

## 4. Flujo de gestión de inventario

Recorrido de un usuario autenticado desde que entra al backoffice hasta que completa una orden de entrada o de salida, con los puntos donde se instrumenta. Las rutas son las reales del backoffice y de la API.

```
 Login ──► Sesión validada ──► /inventario/ingredientes ──► /inventario/ordenes/entrada ──► POST /inventory/orders/inbound
 (P1)        (P2)                  (P3)                         o /salida (P4, P5)              o /outbound (P6–P10)
```

| # | Paso del flujo | Qué ocurre en el código | Punto de instrumentación | Evento(s) | Clasificación |
|---|---|---|---|---|---|
| P1 | Inicio de sesión | `POST /auth/login` valida las credenciales y devuelve el JWT | Resultado del login | `login_succeeded` / `login_failed` | Oportunidad |
| P2 | Acceso a una vista protegida | `SessionProvider` valida el token con `GET /auth/me`; un token caducado o revocado devuelve al login | Validación de la sesión | `session_expired`, `auth_token_rejected` | Oportunidad |
| P3 | Consulta del stock | `/inventario/ingredientes` carga `GET /inventory/products` | La vista se abre | `page_viewed` | Oportunidad |
| P4 | Rellenar el formulario de entrada o de salida | Validación en el navegador (`lib/inventory-validation.ts`) antes de enviar | Errores de validación del formulario; salir sin enviar | `form_validation_failed`, `form_abandoned` | Oportunidad |
| P5 | Ver el stock antes de una salida | El panel de stock pide `GET /inventory/products/{id}` | — (lo cubren P3 y P8) | — | — |
| P6 | Envío de la orden con datos inválidos | La API responde 422 (`invalid_request`) o 404 (`ingredient_not_found`) | La API rechaza la orden por validación | `order_validation_failed` | Oportunidad |
| P7 | Intento de editar el stock fuera de una orden | La API responde 405, o 422 con `current_stock` en el cuerpo | La API rechaza la edición directa | **`direct_stock_edit_rejected`** | **Obligatorio** |
| P8 | Salida sin stock suficiente | `create_exit` calcula el stock con bloqueo y responde 400 `insufficient_stock` antes de escribir | La API rechaza la salida | `outbound_order_rejected` | Oportunidad |
| P9 | Orden registrada | `commit` de la entrada o la salida | Después del `commit` | **`inbound_order_created`**, **`outbound_order_created`** o **`stock_waste_registered`** | **Obligatorio** |
| P10 | Efectos de la orden | Tras el `commit`: el stock resultante frente al mínimo (salidas) y el coste unitario frente al histórico (entradas) | Comprobaciones posteriores al `commit` | **`stock_threshold_triggered`**, **`ingredient_price_variance_detected`** | **Obligatorio** |

**Cobertura del flujo:** 9 puntos de instrumentación (P5 no necesita evento propio). Incluyen los tres que exige el enunciado: intentos directos de modificar el stock (P7), validaciones fallidas (P4 y P6) y activaciones del umbral mínimo (P10). Con `requestId`, los eventos del navegador (P3, P4) se unen con los de la API (P6 a P10) de la misma petición, y con `sessionId`, con los de todo el recorrido.

**En la fase de captura**, P1, P2 y P6 a P10 se emiten en el backoffice al recibir la respuesta de la API de cada paso. El rechazo de P7 lo provoca la acción "Ajustar stock" (§3.2).

## 5. Catálogo de oportunidades identificadas

Eventos propuestos por este plan, agrupados por categoría. Para cada uno: emisor, cuándo se dispara, la frase de la regla de oro y el responsable de la decisión. Todos son **oportunidades identificadas**; los obligatorios están en la sección 3. El emisor es el de la fase de captura (§2.4); los eventos que siguen en la API esperan a su emisor (sección 13).

### 5.1 Inventario

- **`order_validation_failed`** — Navegador, al recibir la respuesta de la API — la API rechaza una orden de entrada o de salida por datos inválidos: 422 `invalid_request` o 404 `ingredient_not_found`.
  *"Capturamos `order_validation_failed` porque necesitamos saber qué productos y qué campos acumulan más errores de validación al registrar órdenes, lo que nos permite tomar la decisión de corregir esos datos de catálogo o reforzar la capacitación sobre esos productos."* — Jake.
- **`outbound_order_rejected`** — Navegador, al recibir la respuesta de la API — la API rechaza una salida porque supera el stock disponible (400 `insufficient_stock`).
  *"Capturamos `outbound_order_rejected` porque necesitamos saber en qué productos y locales el stock registrado no alcanza para lo que la cocina dice haber consumido, señal de entradas sin registrar o de un stock que no refleja la realidad física, lo que nos permite tomar la decisión de ordenar un conteo físico de ese producto en ese local."* — Felipe.
- **`product_created`** — API — tras el `commit` de `POST /api/v1/inventory/products`.
  *"Capturamos `product_created` porque necesitamos saber cuánto y en qué categorías crece el catálogo de ingredientes de cada país, lo que nos permite tomar la decisión de revisar las altas que duplican productos existentes antes de que fragmenten el histórico de consumo y de precios."* — Lucía.

### 5.2 Autenticación y sesión

- **`login_succeeded`** — Navegador, al recibir la respuesta de la API — `POST /auth/login` emite un token.
  *"Capturamos `login_succeeded` porque necesitamos saber cuántos usuarios de cada rol usan el backoffice y en qué franjas horarias, lo que nos permite tomar la decisión de planificar capacitación para los roles que apenas lo usan y concentrar las ventanas de mantenimiento en las horas sin actividad."* — Jake y Nicolás.
- **`login_failed`** — Navegador, al recibir la respuesta de la API — `POST /auth/login` responde 401 `invalid_credentials` o 403 `inactive_user`.
  *"Capturamos `login_failed` porque necesitamos saber cuántos intentos fallidos hay por día y si se concentran en una misma cuenta en poco tiempo (posible fuerza bruta) o se reparten (olvido de contraseña), lo que nos permite tomar la decisión de añadir bloqueo temporal por intentos o de promover la recuperación de contraseña."* — Nicolás.
- **`session_expired`** — Navegador, al recibir la respuesta de la API — una petición llega con un token caducado (401 `token_expired`).
  *"Capturamos `session_expired` porque necesitamos saber con qué frecuencia la sesión caduca en mitad del trabajo de un operador, lo que nos permite tomar la decisión de ajustar `ACCESS_TOKEN_EXPIRE_MINUTES` o de implementar la renovación del token."* — Nicolás.
- **`auth_token_rejected`** — Navegador, al recibir la respuesta de la API — una petición llega con un token inválido (401 `invalid_token`) o revocado tras un cambio de contraseña (401 `session_revoked`).
  *"Capturamos `auth_token_rejected` porque necesitamos saber si llegan tokens manipulados o sesiones ya revocadas que siguen intentando entrar, lo que nos permite tomar la decisión de investigar el origen y, si se repite, rotar `SECRET_KEY`."* — Nicolás.
- **`logout_completed`** — Navegador — el usuario cierra sesión desde el menú de la cuenta.
  *"Capturamos `logout_completed` porque necesitamos saber qué proporción de sesiones se cierran explícitamente y cuántas se dejan abiertas hasta caducar, lo que nos permite tomar la decisión de activar el cierre automático por inactividad en los dispositivos compartidos de los locales."* — Nicolás y Jake.
- **`user_registered`** — Navegador, al recibir la respuesta de la API — tras crear una cuenta con `POST /users`, que hoy es un registro abierto.
  *"Capturamos `user_registered` porque necesitamos saber cuántas cuentas se crean por autorregistro y a qué ritmo, lo que nos permite tomar la decisión de cerrar el registro abierto y pasar a altas aprobadas por un administrador."* — Nicolás.
- **`user_access_changed`** — API — un administrador cambia el rol o activa o desactiva una cuenta (`PUT /users/{id}` con `role` o `is_active`), o se elimina una cuenta (`DELETE /users/{id}`: la propia o, si es admin, cualquiera).
  *"Capturamos `user_access_changed` porque necesitamos saber quién concede o retira permisos de administrador y con qué frecuencia, lo que nos permite tomar la decisión de revisar los accesos privilegiados y exigir aprobación doble si se conceden fuera de un proceso."* — Nicolás.
- **`password_reset_requested`** — API — `POST /auth/forgot-password`, exista o no la cuenta.
  *"Capturamos `password_reset_requested` porque necesitamos saber cuántos usuarios olvidan su contraseña y si hay ráfagas de solicitudes contra cuentas que no existen (enumeración), lo que nos permite tomar la decisión de reforzar la formación sobre credenciales o de limitar las solicitudes por origen."* — Nicolás y Jake.
- **`password_reset_completed`** — Navegador, al recibir la respuesta de la API — `POST /auth/reset-password` cambia la contraseña.
  *"Capturamos `password_reset_completed` porque necesitamos saber qué proporción de las solicitudes de recuperación terminan en una contraseña nueva, lo que nos permite tomar la decisión de simplificar el flujo de recuperación si la mayoría se queda a medias."* — Nicolás.
- **`password_reset_link_rejected`** — Navegador, al recibir la respuesta de la API — un enlace de recuperación se rechaza por inválido, caducado o ya usado (`invalid_reset_token`, `reset_token_expired`, `reset_token_used`).
  *"Capturamos `password_reset_link_rejected` porque necesitamos saber cuántos enlaces caducan antes de usarse o se reutilizan, lo que nos permite tomar la decisión de ajustar `PASSWORD_RESET_EXPIRE_MINUTES` o el texto del correo."* — Nicolás.
- **`password_changed`** — Navegador, al recibir la respuesta de la API — el propio usuario cambia su contraseña con `POST /auth/change-password`.
  *"Capturamos `password_changed` porque necesitamos saber con qué frecuencia el personal renueva su contraseña por iniciativa propia, lo que nos permite tomar la decisión de exigir una renovación periódica o no hacerlo."* — Nicolás.

### 5.3 Navegación y abandono de flujos

- **`page_viewed`** — Navegador — el backoffice muestra una vista protegida o pública, también al navegar sin recargar.
  *"Capturamos `page_viewed` porque necesitamos saber qué secciones visitan más los operadores y desde qué rol, lo que nos permite tomar la decisión de reordenar el menú, priorizar mejoras en las secciones más usadas y retirar las que nadie usa (como la herramienta de pruebas `/funciones`)."* — Nicolás.
- **`form_validation_failed`** — Navegador — un formulario bloquea el envío por errores de validación en el navegador.
  *"Capturamos `form_validation_failed` porque necesitamos saber qué campos de qué formularios provocan más errores antes de enviar, lo que nos permite tomar la decisión de rediseñar esos campos (ayudas, valores por defecto, unidades visibles)."* — Nicolás y Jake.
- **`form_abandoned`** — Navegador — el usuario empieza un formulario (modifica al menos un campo) y sale de la vista o cierra el modal sin enviarlo.
  *"Capturamos `form_abandoned` porque necesitamos saber qué flujos se abandonan a la mitad y en qué campo, lo que nos permite tomar la decisión de simplificar o dividir esos formularios."* — Nicolás y Felipe.
- **`list_filter_applied`** — Navegador — el usuario cambia un filtro en el historial de órdenes, el gestor de incidencias o el directorio de proveedores.
  *"Capturamos `list_filter_applied` porque necesitamos saber qué filtros usan de verdad los operadores en cada lista, lo que nos permite tomar la decisión de trasladar esos filtros a la API con paginación y de fijar los filtros por defecto."* — Nicolás.
- **`list_page_extended`** — Navegador — el usuario pulsa "Mostrar más" en una lista larga.
  *"Capturamos `list_page_extended` porque necesitamos saber hasta qué profundidad recorren los operadores el historial y el gestor, lo que nos permite tomar la decisión de cuántas filas mostrar de entrada y si hace falta un buscador o paginación en la API."* — Nicolás.

### 5.4 Rendimiento

- **`api_latency_recorded`** — Navegador, al recibir la respuesta de la API — una medición de duración por petición. Es el middleware de timing que ya existe (`app/core/timing.py`), convertido en evento.
  *"Capturamos `api_latency_recorded` porque necesitamos saber qué endpoints son lentos con el volumen real y con qué frecuencia se llaman, lo que nos permite tomar la decisión de dónde cachear, paginar u optimizar consultas, y de fijar objetivos de latencia por endpoint."* — Nicolás.
- **`page_performance_recorded`** — Navegador — las métricas de carga de una vista (LCP, CLS, INP y tiempo hasta mostrar los datos).
  *"Capturamos `page_performance_recorded` porque necesitamos saber cómo de rápido carga el backoffice en los dispositivos y redes reales de los locales, no solo en las mediciones de laboratorio, lo que nos permite tomar la decisión de priorizar optimizaciones por vista y fijar un presupuesto de rendimiento."* — Nicolás.
- **`cache_stats_recorded`** — API — resumen periódico de aciertos y fallos de cada caché del inventario.
  *"Capturamos `cache_stats_recorded` porque necesitamos saber qué proporción de lecturas del inventario sale de la caché con los TTL actuales, lo que nos permite tomar la decisión de ajustar los TTL o retirar una caché que no acierta."* — Nicolás.

### 5.5 Errores

- **`api_error_returned`** — Navegador, al recibir la respuesta de la API — cualquier respuesta 4xx de la API, con su código de error.
  *"Capturamos `api_error_returned` porque necesitamos saber qué códigos de error devuelve cada endpoint y con qué frecuencia, lo que nos permite tomar la decisión de corregir los flujos de la interfaz que provocan errores evitables y detectar integraciones mal construidas."* — Nicolás.
- **`server_error_occurred`** — API — una respuesta 500 (`internal_error`) por una excepción no controlada.
  *"Capturamos `server_error_occurred` porque necesitamos saber en qué endpoint y con qué tipo de excepción falla la API, lo que nos permite tomar la decisión de atender el fallo de inmediato y priorizar su corrección frente a otro trabajo."* — Nicolás.
- **`frontend_error_captured`** — Navegador — un error de JavaScript no controlado o una vista que muestra su pantalla de error (`error.tsx`).
  *"Capturamos `frontend_error_captured` porque necesitamos saber qué errores sufren los operadores sin que nadie los reporte, lo que nos permite tomar la decisión de priorizar la corrección de los que afectan a más sesiones."* — Nicolás.
- **`api_connection_failed`** — Navegador, al recibir la respuesta del intermediario — el intermediario no consigue respuesta de la API (502 `api_unavailable`), la API tarda demasiado (504 `api_timeout`) o el intermediario no está configurado (500 `api_not_configured`).
  *"Capturamos `api_connection_failed` porque necesitamos saber cuándo y durante cuánto tiempo el backoffice se queda sin API, lo que nos permite tomar la decisión de abrir un incidente de disponibilidad y revisar el despliegue."* — Nicolás.
- **`email_delivery_failed`** — Proceso (tarea en segundo plano de la API) — el envío de un correo falla, o no se envía porque falta `RESEND_API_KEY`.
  *"Capturamos `email_delivery_failed` porque necesitamos saber cuántos correos de recuperación no llegan a salir, lo que nos permite tomar la decisión de verificar el dominio de envío en Resend o de corregir la configuración del entorno."* — Nicolás.

### 5.6 Otras áreas del negocio

**Directorio de proveedores**

- **`supplier_created`** — Navegador, al recibir la respuesta de la API — tras dar de alta un proveedor (`POST /suppliers`).
  *"Capturamos `supplier_created` porque necesitamos saber cuántos proveedores nuevos entran por país y categoría, lo que nos permite tomar la decisión de consolidar categorías con demasiados proveedores para negociar volumen."* — Lucía.
- **`supplier_rate_updated`** — Navegador, al recibir la respuesta de la API — tras cambiar la tarifa de un proveedor (`PATCH /suppliers/{id}/rate`).
  *"Capturamos `supplier_rate_updated` porque necesitamos saber qué proveedores cambian su tarifa, con qué frecuencia y en qué porcentaje, lo que nos permite tomar la decisión de renegociar antes de que el cambio llegue a la factura."* — Lucía.
- **`supplier_status_changed`** — Navegador, al recibir la respuesta de la API — tras suspender o reactivar un proveedor (`PATCH /suppliers/{id}/status`).
  *"Capturamos `supplier_status_changed` porque necesitamos saber cuántos proveedores se suspenden y en qué categorías y países, lo que nos permite tomar la decisión de buscar proveedores alternativos donde una suspensión deja una categoría sin cobertura."* — Lucía.
- **`supplier_deleted`** — API — tras borrar un proveedor (`DELETE /suppliers/{id}`).
  *"Capturamos `supplier_deleted` porque necesitamos saber cuándo se borra un proveedor que podría tener entregas en el histórico, lo que nos permite tomar la decisión de sustituir el borrado por la suspensión si se pierde trazabilidad."* — Lucía.

**Gestor de incidencias**

- **`incident_created`** — Navegador, al recibir la respuesta de la API — tras registrar una incidencia (`POST /incidents`).
  *"Capturamos `incident_created` porque necesitamos saber qué categorías de incidencia se concentran en qué sedes y con qué origen, lo que nos permite tomar la decisión de dónde enfocar las visitas de supervisión y el mantenimiento preventivo."* — Felipe.
- **`incident_status_changed`** — Navegador, al recibir la respuesta de la API — tras cambiar el estado de una incidencia (`PATCH /incidents/{id}/status`).
  *"Capturamos `incident_status_changed` porque necesitamos saber cuánto tarda cada sede en pasar una incidencia de `open` a `in_progress` y a `resolved`, lo que nos permite tomar la decisión de fijar tiempos objetivo de respuesta y apoyar a las sedes que no los cumplen."* — Felipe.
- **`incident_transition_rejected`** — Navegador, al recibir la respuesta de la API — la API rechaza un cambio de estado no permitido (400 `invalid_transition`).
  *"Capturamos `incident_transition_rejected` porque necesitamos saber si los usuarios intentan transiciones que el ciclo de vida no permite (por ejemplo, reabrir una incidencia resuelta), lo que nos permite tomar la decisión de revisar el ciclo de vida o explicarlo mejor en la interfaz."* — Felipe y Jake.

**Analizador del CSV de incidentes**

- **`incident_report_analyzed`** — Navegador, al recibir la respuesta de la API — tras analizar un CSV con `POST /incidents/analyze`.
  *"Capturamos `incident_report_analyzed` porque necesitamos saber qué proporción de filas de los reportes de los locales es inválida y por qué regla, lo que nos permite tomar la decisión de capacitar a los locales que envían reportes con más errores."* — Jake y Felipe.
- **`incident_report_exported`** — API — tras descargar `results.csv` con `GET /incidents/results/export`.
  *"Capturamos `incident_report_exported` porque necesitamos saber si alguien usa de verdad el resumen exportado o se queda en la pantalla, lo que nos permite tomar la decisión de mantener la exportación o sustituirla por un envío automático del resumen."* — Felipe.

### 5.7 Procesos internos

- **`api_instance_started`** — Proceso — al terminar el arranque de la API (`lifespan`).
  *"Capturamos `api_instance_started` porque necesitamos saber cuándo se reinicia la API y con qué configuración (correo activo o no, siembra del directorio de proveedores), lo que nos permite tomar la decisión de investigar los reinicios inesperados y bloquear despliegues con configuración incompleta."* — Nicolás.
- **`data_seed_executed`** — Proceso — al terminar un script de carga de datos (`uv run seed`, `seed-inventory`, `scripts/seed_incidents.py`, `scripts/seed_volume.py`).
  *"Capturamos `data_seed_executed` porque necesitamos saber cuándo y cuántos datos entran fuera del flujo de la API, que no deja trazabilidad por usuario ni invalida la caché, lo que nos permite tomar la decisión de restringir estos scripts en producción y de excluir esos datos de los indicadores de negocio."* — Nicolás.

## 6. Resumen del catálogo

| Categoría | Obligatorios | Oportunidades identificadas | Total |
|---|---|---|---|
| Inventario | 6 | 3 | 9 |
| Autenticación y sesión | — | 11 | 11 |
| Navegación y abandono | — | 5 | 5 |
| Rendimiento | — | 3 | 3 |
| Errores | — | 5 | 5 |
| Otras áreas del negocio | — | 9 | 9 |
| Procesos internos | — | 2 | 2 |
| **Total** | **6** | **38** | **44** |

Por emisor, en la fase de captura: 34 del navegador, 7 de la API y 3 de procesos (la tarea de correo, el arranque de la API y los scripts de carga). El diseño original asignaba 32 a la API, 8 al navegador y 1 al BFF (§2.4). Las preguntas del RFI quedan cubiertas así:

| Pregunta | Evento(s) |
|---|---|
| ¿Cuántas órdenes de salida se registran por día? | `outbound_order_created` + `stock_waste_registered` |
| ¿Qué productos acumulan más errores de validación? | `order_validation_failed` (y `form_validation_failed`, antes de enviar) |
| ¿Hay usuarios intentando modificar el stock directamente? | `direct_stock_edit_rejected` |
| ¿Cuándo se disparan más las alertas de stock mínimo? | `stock_threshold_triggered` |
| ¿Cuántos intentos de login fallidos hay por día? | `login_failed` |
| ¿Qué secciones visitan más los operadores? | `page_viewed` |
| ¿Hay flujos que se abandonan a la mitad? | `form_abandoned` |

## 7. Event Envelope

Todo evento, sea cual sea su emisor, es un objeto JSON con los campos siguientes. **Ningún campo puede faltar:** cuando un dato no aplica, su valor es `null`.

| Campo | Tipo | Valor |
|---|---|---|
| `eventId` | string (UUID v4) | Identificador único del evento, generado por el emisor. El almacenamiento descarta los duplicados por este campo. |
| `timestamp` | string (ISO 8601) | Momento del hecho, en UTC y con milisegundos: `2026-11-18T17:36:46.123Z`. Lo pone el emisor cuando ocurre el hecho, no cuando se envía. |
| `sessionId` | string (UUID v4) o `null` | Sesión del navegador: un UUID que el backoffice crea **al iniciar sesión** y guarda en `sessionStorage` (uno por pestaña; una pestaña nueva con la sesión ya iniciada crea el suyo al validarla). Se borra al cerrar la sesión o cuando caduca. Viaja en la cabecera `X-Session-Id`. Es `null` antes del login (vistas públicas), en los procesos y en las peticiones que no vienen del backoffice. |
| `userId` | string (UUID) o `null` | La cuenta que actúa: el `sub` del token (`User.id` en TinyDB). Es un identificador seudónimo, nunca el email ni el nombre. Es `null` si no hay usuario autenticado. Cada ficha (sección 15) indica qué valor lleva. |
| `event_type` | string | El tipo del evento, con la taxonomía de la sección 2.3. Cada esquema de `event-schemas.json` lo fija con `const`. |
| `schemaVersion` | string (SemVer) | Versión del esquema **de ese evento**. Todos empiezan en `1.0.0`. Sube la versión menor al añadir una propiedad opcional, y la mayor al quitar o renombrar una propiedad, cambiar su tipo o hacer obligatoria una que no lo era. |
| `requestId` | string (UUID v4) o `null` | Correlación entre el frontend, el backend y los logs. Lo crea el navegador por cada llamada a la API, en la cabecera `X-Request-Id`; el BFF lo reenvía; la API lo crea si falta, lo devuelve en la respuesta y lo pone en sus eventos y en su línea de `api.timing`. Es `null` si el evento no nace de una petición, como una vista o un proceso. |
| `properties` | object | Los datos propios del evento. **Solo admite las claves del allowlist de su ficha**: el esquema lo impone con `additionalProperties: false`. |
| `source` | string | Emisor: `api`, `bff`, `browser` o `process`. Es un añadido de este plan. |
| `environment` | string | `development`, `staging` o `production`. Es un añadido de este plan, para que los datos de prueba, como las semillas de volumen `VOL-`, no se mezclen con los de producción. |

**Nombres de los campos.** Los ocho primeros llevan exactamente los nombres del enunciado, así que el envelope mezcla camelCase (`eventId`, `sessionId`, `schemaVersion`…) con `event_type` en snake_case. Se respetan tal cual porque el enunciado los fija como identificadores. Todo lo demás sigue snake_case, como el briefing: los `event_type` y todas las claves de `properties`. Los dos campos añadidos (`source` y `environment`) son de una sola palabra, así que no suman otra convención.

**Ejemplo completo** (`stock_waste_registered`):

```json
{
  "eventId": "5b2e8f4a-1c3d-4e6f-9a7b-8c9d0e1f2a3b",
  "timestamp": "2026-11-18T17:36:46.123Z",
  "sessionId": "0f8e7d6c-5b4a-4392-8170-6e5d4c3b2a19",
  "userId": "d445afb4-d2f2-4caa-bbf5-9e0023fcfbb2",
  "event_type": "stock_waste_registered",
  "schemaVersion": "1.0.0",
  "requestId": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "properties": {
    "order_id": 13319,
    "location_id": 3,
    "country": "CO",
    "product_id": 12,
    "product_category": "proteína",
    "quantity": 1.2,
    "unit": "kg",
    "currency": "COP",
    "reason": "expired",
    "stock_after": 30.4
  },
  "source": "browser",
  "environment": "production"
}
```

### 7.1 Reglas para quien instrumente

1. **Validar antes de emitir.** El emisor valida cada evento contra `event-schemas.json`. Un evento que no cumple su esquema, por ejemplo porque lleva una clave fuera del allowlist, **no se emite**: se descarta y se cuenta en el log del emisor. Nunca se recorta ni se corrige en silencio.
2. **Las propiedades opcionales se omiten.** Si una propiedad opcional no tiene valor, la clave no se envía. Los `null` son solo para los campos del envelope.
3. **Correlación de extremo a extremo.** Para que `requestId` y `sessionId` lleguen a la API, el navegador añade `X-Request-Id` y `X-Session-Id` a cada llamada (`lib/api-client.ts`). El BFF debe reenviarlas, porque hoy solo copia `Content-Type`, `Accept` y `Authorization`. La API debe leerlas y crear `X-Request-Id` si falta.
4. **Los eventos de negocio de la API se emiten después del `commit`** (sección 2.4). Los rechazos se emiten al construir la respuesta de error. En la fase de captura, el backoffice los emite al recibir esa respuesta, con el `requestId` de la llamada.
5. **Las rutas siempre van como plantilla:** `/api/v1/incidents/{incident_id}` o `/talento/candidates/[id]`, nunca con ids reales ni query string.

### 7.2 Cómo está organizado `event-schemas.json`

Es un JSON Schema **draft-07** válido. Un evento es válido si cumple exactamente uno de los 44 esquemas de `oneOf`. El campo `event_type` lo dirige al suyo.

| Ruta | Contenido |
|---|---|
| `definitions/envelope` | Los campos de la tabla anterior, con `additionalProperties: false` |
| `definitions/properties` | Las propiedades que comparten varios eventos (`location_id`, `country`, `product_category`, `route`, `account_fingerprint`…), con su tipo y su dominio |
| `definitions/events/<event_type>` | Un esquema por evento: el envelope (`allOf`), `event_type`, `schemaVersion` y `source` fijos con `const`, y `properties` con sus obligatorias y su allowlist (`additionalProperties: false`). Incluye un ejemplo válido en `examples`. |
| Claves `x-*` de cada evento | Anotaciones documentales que los validadores ignoran: `x-classification` (`obligatorio` u `oportunidad`), `x-category`, `x-emitter`, `x-trigger`, `x-pii`, `x-delivery` (modo, cadencia, justificación y, si aplica, throttle; secciones 9 y 10) y, para la tabla de almacenamiento, `x-level`, `x-value` y `x-message` (sección 14.2) |

## 8. Datos sensibles y PII

Estos eventos describen productos, locales y el uso del sistema, no a las personas. El allowlist es la primera defensa: una clave que no está en el esquema no puede viajar. Sobre lo que sí viaja se aplican estas reglas.

### 8.1 Lo que nunca se emite

- Emails, nombres, teléfonos y direcciones: los de los perfiles, los de los proveedores y los de los destinatarios de correo.
- Contraseñas, tokens JWT, enlaces o tokens de recuperación y claves de configuración.
- Texto libre escrito por un usuario: títulos y descripciones de incidencias, notas, textos de búsqueda y valores escritos en formularios. De los formularios solo viajan los **nombres** de los campos.
- Cuerpos de petición y de respuesta, y mensajes de las excepciones de la API.
- La IP completa y el user agent completo.
- Datos de la herramienta de talento (candidatos de una API externa): ni sus ids reales, porque `page_viewed` usa la plantilla `/talento/candidates/[id]`.

### 8.2 Niveles y técnicas

| Nivel | Qué es | Técnica | Dónde |
|---|---|---|---|
| **Ninguno** | Datos de negocio y técnicos sin relación con una persona | — | La mayoría de las propiedades |
| **Seudónimo** | Identifica una cuenta sin revelar quién es | UUID internos: `userId` (envelope), `new_user_id`, `target_user_id` | Autenticación y cualquier evento con usuario |
| **Sanitizado** | Dato personal transformado antes de salir del emisor | `account_fingerprint`: HMAC-SHA256 del email normalizado con la clave `TELEMETRY_HASH_KEY` (distinta de `SECRET_KEY`), truncado a 16 caracteres hexadecimales. `client_network`: IP truncada a /24 (IPv4) o /48 (IPv6). `message_sanitized`: mensaje recortado a 200 caracteres, con emails, números de 4 o más cifras y UUID sustituidos por `[redacted]`. | `password_reset_requested`, `frontend_error_captured` (y `login_failed` 1.0.0, cuando lo emita la API; la 2.0.0 del navegador no lleva ni huella ni red) |

**Por qué HMAC y no un hash simple:** el email tiene pocas variantes probables, así que un SHA-256 sin clave se podría revertir probando emails conocidos. Con una clave secreta del servidor no se puede. Si la clave se rota, las huellas anteriores dejan de agruparse con las nuevas. Es aceptable, porque solo se usan para detectar ráfagas en ventanas cortas.

**Por qué `userId` es `null` en `login_failed` aunque la cuenta exista:** con el `userId` relleno, la telemetría revelaría qué emails tienen cuenta, que es justo lo que la respuesta neutra de la API oculta. La agrupación por cuenta la da `account_fingerprint` cuando el evento lo emite la API. En la fase de captura, `login_failed` 2.0.0 solo lleva el motivo (sección 13).

## 9. Estrategia de entrega: stream o batch

**Criterio:** la urgencia de la decisión que alimenta cada evento, o la necesidad operativa de detectarlo rápido. No la preferencia técnica.

- **Stream:** el evento llega a quien decide en **segundos**, como alerta o en un panel en vivo, porque la decisión solo sirve si se toma mientras el problema ocurre: un ataque, una caída, un local sin stock o un precio anómalo.
- **Batch:** el evento se guarda y se procesa en **lotes periódicos** (cada hora, o a diario a las 02:00 hora local), porque la decisión se toma con el acumulado de días o semanas.

**Todo evento, también los de stream, se guarda para el análisis batch.** Stream añade la ruta rápida; no sustituye al histórico. `stock_threshold_triggered`, por ejemplo, avisa en el momento y además alimenta en batch el ajuste del mínimo.

**Transporte frente a procesamiento:** el navegador agrupa sus eventos para enviarlos (hasta 20 eventos o 10 segundos, lo que ocurra primero, y `navigator.sendBeacon` al ocultar o cerrar la pestaña). Eso es una optimización del envío, no "batch" en el sentido de esta sección: un evento de stream emitido por el navegador sale en ese mismo envío, así que llega en 10 segundos como máximo.

**Resumen:** **12 eventos en stream** (seguridad, disponibilidad y alertas de negocio que no pueden esperar) y **32 en batch** (28 diarios y 4 cada hora). De los 6 obligatorios, 2 van en stream (`stock_threshold_triggered` e `ingredient_price_variance_detected`) y 4 en batch.

| `event_type` | Modo | Cadencia | Justificación (urgencia de la decisión) |
|---|---|---|---|
| `stock_threshold_triggered` | **stream** | segundos | Un local que se queda corto de un ingrediente clave necesita reponer **ese mismo día**: el supervisor debe enterarse en minutos, no al día siguiente. Además alimenta en batch el ajuste del mínimo. |
| `ingredient_price_variance_detected` | **stream** | segundos | Es una alerta para Lucía y Mariana: renegociar o cambiar de proveedor **antes** de aceptar más entregas al precio nuevo. Un día de retraso son más compras al precio anómalo. |
| `login_failed` | **stream** | segundos | Un ataque de fuerza bruta se detiene en minutos o no se detiene: la decisión (bloqueo temporal) solo sirve si llega a tiempo. |
| `auth_token_rejected` | **stream** | segundos | Tokens manipulados o sesiones revocadas que insisten son un posible incidente de seguridad: investigar y rotar `SECRET_KEY` no puede esperar al día siguiente. |
| `user_registered` | **stream** | segundos | Con el registro abierto, una cuenta creada por alguien ajeno ya puede leer el inventario: hay que poder revisarla y desactivarla en minutos. |
| `user_access_changed` | **stream** | segundos | Una concesión de administrador fuera de proceso es una escalada de privilegios: se revisa en el momento. |
| `password_reset_requested` | **stream** | segundos | Una ráfaga contra cuentas inexistentes (enumeración) solo se frena si se detecta mientras ocurre. |
| `server_error_occurred` | **stream** | segundos | Un 500 es un fallo de la API que hay que atender ya: puede estar impidiendo registrar órdenes en todos los locales. |
| `api_connection_failed` | **stream** | segundos | Sin API, ningún local puede registrar órdenes: es un incidente de disponibilidad que se abre en minutos. |
| `email_delivery_failed` | **stream** | segundos | Hay un usuario esperando su enlace de recuperación ahora mismo; una configuración rota afecta a todos los siguientes. |
| `api_instance_started` | **stream** | segundos | Un reinicio inesperado o un arranque con el correo desactivado en producción hay que verlo en el momento, antes de que lo noten los usuarios. |
| `data_seed_executed` | **stream** | segundos | Un script de carga ejecutado contra producción mete datos sin trazabilidad en los indicadores de negocio: hay que detectarlo y retirarlos antes del batch diario. |
| `inbound_order_created` | **batch** | diario (cierre 02:00 hora local) | Consolidar compras y negociar precios son decisiones semanales o mensuales de Lucía; nadie actúa sobre una entrega concreta en minutos. |
| `outbound_order_created` | **batch** | diario (cierre 02:00 hora local) | La sugerencia automática de pedidos se recalcula con el consumo acumulado del día; un consumo concreto no cambia la decisión en minutos. |
| `stock_waste_registered` | **batch** | diario (cierre 02:00 hora local) | Priorizar auditorías de merma es una decisión semanal por local; la merma de hoy ya ocurrió y no se corrige en minutos. |
| `direct_stock_edit_rejected` | **batch** | diario (cierre 02:00 hora local) | Reforzar capacitación o permisos es una decisión semanal de Jake; el sistema ya rechazó el intento, no hay daño que contener en minutos. |
| `order_validation_failed` | **batch** | diario (cierre 02:00 hora local) | Corregir datos de catálogo y capacitar se decide con el acumulado de la semana. |
| `outbound_order_rejected` | **batch** | diario (cierre 02:00 hora local) | El conteo físico se programa con el acumulado del día por producto y local; el rechazo ya protegió el stock. |
| `product_created` | **batch** | diario (cierre 02:00 hora local) | Revisar duplicados del catálogo es una tarea periódica de Compras. |
| `login_succeeded` | **batch** | diario (cierre 02:00 hora local) | Planificar capacitación y ventanas de mantenimiento usa patrones de semanas. |
| `session_expired` | **batch** | diario (cierre 02:00 hora local) | Ajustar la duración del token es una decisión de configuración que se toma con semanas de datos. |
| `logout_completed` | **batch** | diario (cierre 02:00 hora local) | El cierre automático por inactividad se decide con el patrón de semanas. |
| `password_reset_completed` | **batch** | diario (cierre 02:00 hora local) | Simplificar el flujo de recuperación se decide con la tasa semanal. |
| `password_reset_link_rejected` | **batch** | diario (cierre 02:00 hora local) | Ajustar la caducidad del enlace o el texto del correo es una decisión de configuración. |
| `password_changed` | **batch** | diario (cierre 02:00 hora local) | Exigir o no la renovación periódica es una política, no una reacción. |
| `page_viewed` | **batch** | diario (cierre 02:00 hora local) | Reordenar el menú o retirar secciones se decide con semanas de uso. |
| `form_validation_failed` | **batch** | diario (cierre 02:00 hora local) | Rediseñar campos se decide con el acumulado. |
| `form_abandoned` | **batch** | diario (cierre 02:00 hora local) | Simplificar formularios se decide con el acumulado. |
| `list_filter_applied` | **batch** | diario (cierre 02:00 hora local) | Mover filtros a la API se decide con el uso de semanas. |
| `list_page_extended` | **batch** | diario (cierre 02:00 hora local) | Fijar las filas iniciales o añadir paginación se decide con el acumulado. |
| `api_latency_recorded` | **batch** | cada hora | Decidir dónde cachear o fijar objetivos de latencia usa percentiles por hora y por día. Las caídas, que sí son urgentes, las detectan `server_error_occurred` y `api_connection_failed` en stream. |
| `page_performance_recorded` | **batch** | diario (cierre 02:00 hora local) | Priorizar optimizaciones y fijar presupuestos de rendimiento usa la distribución de días. |
| `cache_stats_recorded` | **batch** | cada hora | Ajustar TTL es una decisión de configuración con tendencias de horas. |
| `api_error_returned` | **batch** | cada hora | Corregir flujos que provocan errores evitables se decide con el acumulado; los errores graves (500) van por su propio evento en stream. |
| `frontend_error_captured` | **batch** | cada hora | La decisión es priorizar correcciones por número de sesiones afectadas, con datos de horas. Un despliegue roto se ve también en `api_error_returned` y en las consultas de soporte. |
| `supplier_created` | **batch** | diario (cierre 02:00 hora local) | Consolidar categorías de proveedores es una decisión trimestral. |
| `supplier_rate_updated` | **batch** | diario (cierre 02:00 hora local) | Renegociar se planifica con el histórico de cambios; la tarifa ya está registrada. |
| `supplier_status_changed` | **batch** | diario (cierre 02:00 hora local) | Buscar proveedores alternativos se decide con la cobertura por categoría, revisada a diario. |
| `supplier_deleted` | **batch** | diario (cierre 02:00 hora local) | Revisar si el borrado debió ser suspensión es una tarea periódica. |
| `incident_created` | **batch** | diario (cierre 02:00 hora local) | Planificar visitas y mantenimiento usa el acumulado por sede. La atención de cada incidencia ya ocurre en el gestor, no en la telemetría. |
| `incident_status_changed` | **batch** | diario (cierre 02:00 hora local) | Los tiempos objetivo de respuesta se fijan y revisan con datos de semanas. |
| `incident_transition_rejected` | **batch** | diario (cierre 02:00 hora local) | Revisar el ciclo de vida o la interfaz se decide con el acumulado. |
| `incident_report_analyzed` | **batch** | diario (cierre 02:00 hora local) | La capacitación por calidad de los reportes es periódica. |
| `incident_report_exported` | **batch** | diario (cierre 02:00 hora local) | Mantener o sustituir la exportación se decide con meses de uso. |

## 10. Throttle y debounce

Los eventos de alta frecuencia se limitan **en el emisor, antes de enviarlos**, con cuatro reglas:

1. **Nunca se limitan los hechos de negocio.** Cada orden, merma o cambio de acceso se emite una vez. El único caso "limitado" es `stock_threshold_triggered`, y lo está por definición: se emite al cruzar el mínimo.
2. **El muestreo debe poder deshacerse.** Si un evento se muestrea, lleva la tasa aplicada (`sample_rate`), para reconstruir los totales.
3. **Lo descartado se cuenta.** El emisor registra en su log cuántos eventos suprimió por throttle, para que un pico no desaparezca sin rastro.
4. **Ventanas por clave.** Se limita la repetición del **mismo** hecho (misma huella, mismo token, mismo formulario), no todos los eventos de un tipo.

| `event_type` | Estrategia |
|---|---|
| `stock_threshold_triggered` | Natural: solo se emite al **cruzar** el mínimo (§3.2), así que un producto bajo no repite la alerta en cada consumo. |
| `login_failed` | Sin muestreo ni límite: cada intento cuenta para detectar la ráfaga. En el navegador, su frecuencia es la de los envíos del formulario de login. |
| `session_expired` | Uno por token: varias peticiones en paralelo con el mismo token caducado (resumen y listado) emiten un solo evento por (`userId`, `iat`) en 60 s. |
| `auth_token_rejected` | Uno por token y motivo cada 60 s (las peticiones en paralelo comparten token). |
| `page_viewed` | Se ignora una segunda vista de la misma ruta en menos de 1 s (doble montaje de React en desarrollo, recargas dobles). |
| `form_validation_failed` | Uno por formulario cada 2 s (doble clic en enviar). |
| `form_abandoned` | Uno por formulario abierto: se emite una sola vez, al salir. |
| `list_filter_applied` | Debounce de 500 ms en los filtros de texto: solo se emite cuando se deja de escribir. |
| `api_latency_recorded` | **Muestreo:** se emite siempre si `duration_ms` ≥ 300 o `status_code` ≥ 400; el resto, 1 de cada 10 peticiones, elegidas por el `requestId` (determinista). `sample_rate` indica la tasa aplicada (1 o 0,1) para reconstruir los recuentos. |
| `page_performance_recorded` | Uno por vista mostrada. |
| `cache_stats_recorded` | Ya es un agregado: uno por caché cada 5 minutos. |
| `api_error_returned` | Un mismo (`route`, `error_code`, `userId`) se emite como máximo una vez cada 10 s: un script que repite la misma petición fallida no multiplica el volumen. |
| `server_error_occurred` | Una vez por `error_fingerprint` cada 60 s, con el recuento en el log del emisor. |
| `frontend_error_captured` | Una vez por `error_fingerprint` y sesión cada 60 s, y como máximo 20 por sesión (un error en bucle no inunda la telemetría). |
| `api_connection_failed` | Una vez por sesión cada 30 s mientras la API no responde. |

El resto de eventos no necesita límite: su frecuencia es la de una acción humana (un envío, un clic) o la de un hecho de negocio.

## 11. Riesgos y exclusiones

### 11.1 Eventos considerados y descartados

Cada uno se descartó porque no supera la regla de oro (no hay decisión concreta que habilite), porque duplica otro evento o por privacidad.

| Evento considerado | Por qué se descarta |
|---|---|
| `profile_updated` (cambio de nombre, teléfono o dirección) | No hay decisión que dependa de él, y sus datos son personales. |
| `product_list_viewed`, `stock_viewed`, `supplier_viewed`, `incident_viewed` (cada lectura de una lista o un detalle) | Duplican `page_viewed` (qué se mira) y `api_latency_recorded` (cuánto cuesta) sin añadir una decisión nueva. |
| `stock_out_reached` (stock a 0) | Ya lo cubre `stock_threshold_triggered`, con `quantity` = 0. |
| `api_request_received` (toda petición) | Duplica `api_latency_recorded`, que ya se emite por petición, con muestreo. |
| `email_sent` (envío correcto) | El total esperado ya sale de `password_reset_requested` con `account_found`; solo los fallos (`email_delivery_failed`) llevan a una decisión. |
| `health_check_performed` (healthcheck de Docker cada pocos segundos) | Ruido de alta frecuencia sin decisión. La disponibilidad la cubren `api_connection_failed` y `api_instance_started`. |
| `candidate_created`, `candidate_updated`, `candidate_note_added` (herramienta de talento) | Usa una API externa de prácticas, no datos de Brasaland, y sus datos son personales (candidatos). La visita a la sección ya la cuenta `page_viewed`. |
| `function_executed` (herramienta `/funciones`) | Es una herramienta de pruebas para desarrolladores. La única decisión (retirarla) ya la alimenta `page_viewed`. |
| `ui_language_changed` | No existe selector de idioma. Además, el briefing exige que el idioma de la interfaz no se mezcle con `country`; si algún día existe, será un evento propio, sin relación con el país del local. |
| `token_refreshed` | No existe renovación de token. Si se implementa a raíz de `session_expired`, se añadirá. |
| `element_clicked`, `page_scrolled` (mapas de calor) | Sin una decisión concreta, mucho volumen y riesgo de privacidad. Los flujos abandonados se miden con `form_abandoned`, que sí responde una pregunta del RFI. |
| Análisis del texto de las incidencias | El título y la descripción son texto libre que puede contener datos de personas (clientes, empleados). Las categorías ya dan la señal de negocio. |

### 11.2 Datos que no se capturan

| Dato | Motivo | Qué se usa en su lugar |
|---|---|---|
| Emails, nombres, teléfonos y direcciones | Privacidad | `userId` seudónimo; `account_fingerprint` (HMAC) cuando hace falta agrupar por cuenta sin sesión |
| Valores de los formularios y textos de búsqueda | Privacidad | Nombres de campo (`invalid_fields`, `last_field`) y longitud del texto (`query_length`) |
| IP completa, geolocalización y user agent completo | Privacidad: permiten identificar a una persona | `client_network` (IP truncada) y `device_class` |
| Cuerpos de petición y mensajes de excepción | Privacidad: pueden llevar datos personales o secretos | Códigos de error, tipo de excepción y `error_fingerprint` |
| Ids reales en las URL | Privacidad: un id de candidato identifica a una persona | Plantillas de ruta (`/talento/candidates/[id]`) |
| El 100 % de las mediciones de latencia | Coste: una por petición | Muestreo 1:10, con todas las lentas y las de error (§10) |
| Un evento por acierto de caché | Coste: una por lectura | `cache_stats_recorded`, un agregado cada 5 minutos |

### 11.3 Riesgos y mitigaciones

| # | Riesgo | Mitigación |
|---|---|---|
| R1 | **Varios eventos obligatorios no pueden emitirse con el modelo actual** (sin precio en las entradas, sin motivo de merma, sin mínimos por local, sin entidad de locales). | No se emiten con valores inventados: la sección 12 dice qué cambio necesita cada uno. Cerrar esas brechas es la primera tarea de la fase de captura. |
| R2 | `userId` es seudónimo, pero sigue siendo un dato personal. | Acceso restringido a los datos crudos: la tabla tiene RLS sin políticas (§14.1). Los eventos no se reescriben: al eliminar una cuenta (`DELETE /users/{id}`), su UUID deja de corresponder a nadie y sus eventos quedan desvinculados sin tocarlos. Si una solicitud de supresión exige borrarlos, se hace con la purga manual de §14.1. La retención se fijará cuando haya un pipeline de agregados. |
| R3 | Los eventos del navegador se pierden (bloqueadores, pestañas cerradas, sin conexión). | Las métricas de navegador se tratan como aproximaciones. **Los hechos de negocio debe emitirlos la API**, que es la fuente de verdad. **Riesgo asumido en la fase de captura:** los emite el backoffice al recibir la respuesta de la API, con cola, reintentos y `sendBeacon` (sección 13). Una pestaña cerrada antes del envío o una orden registrada fuera del backoffice no dejan evento hasta que exista el emisor de la API. |
| R4 | El reloj del navegador puede estar mal. | `timestamp` guarda el momento de la captura; la tabla de ocho columnas no guarda la hora de recepción, que sí queda en el log `api.telemetry`. Los análisis de negocio usarán los `timestamp` de la API cuando exista su emisor. |
| R5 | La telemetría podría romper la operación (latencia o errores al emitir). | Emisión asíncrona, después del `commit` y sin bloquear la respuesta. Un fallo al emitir se registra en el log y nunca hace fallar la petición. |
| R6 | Doble conteo: reintentos o dos emisores del mismo hecho. | Un único emisor por evento (§2.4). Los reintentos conservan el `eventId`, y el almacenamiento descarta duplicados por ese campo. |
| R7 | Datos de prueba mezclados con los reales (semillas `VOL-`, entornos locales). | El campo `environment` del envelope y el evento `data_seed_executed`. Los indicadores de negocio solo usan `production`. |
| R8 | Los esquemas cambian y rompen a sus consumidores. | `schemaVersion` por evento con SemVer (§7). Un cambio mayor convive con la versión anterior durante la transición. |
| R9 | Picos de volumen y de coste (un ataque dispara `login_failed`; un bucle, `frontend_error_captured`). | Límites de §10. `login_failed` no se muestrea a propósito: el coste de un ataque es menor que no verlo. |
| R10 | Rotar `TELEMETRY_HASH_KEY` corta la continuidad de `account_fingerprint`. | Aceptado: la huella solo se usa para detectar ráfagas en ventanas cortas. La clave vive en el entorno, separada de `SECRET_KEY`. |
| R11 | Con varios workers de la API, cada uno lleva sus propios contadores de caché. | `cache_stats_recorded` se emite por proceso y se suma en el almacenamiento. Los contadores son aditivos. |

## 12. Brechas de instrumentación

Lo que necesita el sistema actual para emitir cada evento tal como lo define este plan. Los nombres del briefing se mantienen en los eventos; las tablas dicen cómo se obtienen hoy y qué hay que cambiar.

### 12.1 Equivalencias con el modelo actual

| Briefing (eventos) | Modelo actual (`services/brasaland-api`) |
|---|---|
| `Product`, `product_id` | `Ingredient`, `Ingredient.id` (tabla `ingredients`) |
| `InboundOrder`, `order_id` | `IngredientEntry`, `IngredientEntry.id` (tabla `ingredient_entries`) |
| `OutboundOrder`, `order_id` | `IngredientExit`, `IngredientExit.id` (tabla `ingredient_exits`); motivo `consumption` → `outbound_order_created`, `waste` → `stock_waste_registered` |
| `product_category` | `Ingredient.category`: `meat` → `proteína`, `produce` → `vegetal`, `sauce` → `salsa`, `beverage` → `bebida`, `packaging` → `empaque`, `cleaning` → `limpieza` |
| `unit` | `Ingredient.unit` (`kg`, `unidad`, `litro`: los mismos valores) |
| `location_id` | `location_id` de la orden (1–14), sin entidad propia |
| `country` | Hoy solo existe `Ingredient.country`. Debe salir del **local** (brecha B7) |
| `currency` | Derivada del país del local: `CO` → `COP`, `US` → `USD` |
| `supplier`, `supplier_id` | Directorio de proveedores (`suppliers`, TinyDB). La entrada guarda `supplier_name` como texto (brecha B8) |
| Directorio: `country` `Colombia`/`USA` | `CO`/`US` en los eventos de proveedores |

### 12.2 Cambios necesarios

| # | Eventos afectados | Qué falta hoy | Cambio propuesto |
|---|---|---|---|
| B3 | `stock_threshold_triggered` | No hay mínimos configurables, y el stock es global por ingrediente (decisión D7 del Hito 5), no por local. | Tabla `stock_thresholds` (`product_id`, `location_id`, `min_quantity`) y cálculo del stock **por local** (sumas filtradas por `location_id`) para evaluar el cruce tras cada salida. **Provisional en la fase de captura:** umbral de stock bajo del backoffice por unidad, sobre el stock global (§3.2). |
| B4 | `direct_stock_edit_rejected` | La API rechaza los intentos (405 y 422), pero no los distingue de otros errores. | En los manejadores de 405 y de validación de `app/core/errors.py`, detectar las rutas del inventario y el campo `current_stock`/`stock` en los errores `extra_forbidden`, y emitir el evento. |
| B5 | `inbound_order_created`, `ingredient_price_variance_detected` | Las entradas no tienen coste unitario. | `unit_cost` obligatorio en `IngredientEntryCreate` y en la tabla (en la moneda del local), y una consulta de la media de 90 días por producto y proveedor. **Se cierra en la fase de captura** (`unit_cost`; la media la calcula el backoffice con `GET /orders`). |
| B6 | `stock_waste_registered` | Las salidas solo distinguen `consumption`/`waste`, sin el motivo de la merma. | `waste_reason` (`expired`, `kitchen_error`, `theft_suspected`), obligatorio cuando `reason` = `waste` y prohibido en los consumos. El backoffice añade el desplegable al formulario de salida. **Se cierra en la fase de captura.** |
| B7 | Todos los de inventario (`country`, `currency`) | No hay entidad de locales: `location_id` es un número sin país ni ciudad. | Tabla `locations` (`id` 1–14, `country`, `city`) en Supabase. `country` y `currency` salen del local de la orden. **Provisional en la fase de captura:** salen del país del ingrediente (`Ingredient.country`). |
| B8 | `inbound_order_created`, `ingredient_price_variance_detected` | La entrada guarda el nombre del proveedor, no su id, y el directorio vive en TinyDB. | `supplier_id` en `IngredientEntry`, que referencia al directorio (más fácil tras migrar `suppliers` a PostgreSQL, ya pendiente). **Provisional en la fase de captura:** el backoffice obtiene el `id` del directorio por el nombre elegido, que es único. |
| B9 | Validación de la instrumentación | La semilla actual no cubre el §5 del briefing (3 mermas con motivos distintos, 2 cruces de umbral, 1 variación de precio). | Ampliar `seed-inventory` en la fase de captura con esos casos, una vez cerradas B3, B5 y B6. |
| B10 | `direct_stock_edit_rejected` (decisión "en los locales donde ocurre") | Las cuentas no tienen local asignado. Un `PATCH /products/{id}` no indica local. | `location_id` en el perfil del usuario, para atribuir el intento al local de quien lo hace. Hasta entonces, `location_id` solo se rellena si la petición lo trae. |
| B11 | Todos (`requestId`, `sessionId`) | El navegador no envía `X-Request-Id` ni `X-Session-Id`, el BFF no los reenvía y la API no los lee. | `lib/api-client.ts` añade las dos cabeceras; el BFF las copia; un middleware de la API lee o crea `X-Request-Id`, lo devuelve y lo pone en los eventos y en la línea de `api.timing`. **La fase de captura cierra `X-Request-Id`** (navegador, BFF y `api.timing`); `X-Session-Id` llega con el emisor de la API. |
| B12 | `login_failed`, `password_reset_requested`; todos (`environment`) | No hay clave de huella ni variable de entorno de telemetría. | Variables `TELEMETRY_HASH_KEY` y `TELEMETRY_ENVIRONMENT` en `app/core/config.py` (obligatorias cuando la telemetría esté activa). |
| B13 | `incident_report_exported` | El último análisis se guarda en memoria sin la hora en que se hizo. | Guardar `analyzed_at` junto al resultado en `LastAnalysisRepository`. |

Las brechas B1 (nombres de las entidades) y B2 (categorías) ya quedan resueltas por las equivalencias de §12.1: se traducen al emitir y no requieren cambios de modelo.

## 13. Fase de captura en el backoffice

La primera implementación del plan captura los eventos **en el backoffice** y los envía en lotes a un receptor provisional de la API. El receptor valida el formato y responde 200, sin guardar nada: el almacenamiento es la fase siguiente (sección 14), que mantiene la misma URL, así que el backoffice no cambia.

### 13.1 Cómo se captura

- **Una sola función.** `uis/backoffice/lib/telemetry/` exporta únicamente `track(eventType, properties)`. Ningún otro código del backoffice envía telemetría con `fetch` ni con otra librería.
- **El envelope lo pone el servicio.** Quien llama a `track()` solo pasa el `event_type` y sus `properties`. El servicio añade:

  | Campo | Valor |
  |---|---|
  | `eventId` | UUID v4 generado al capturar el evento |
  | `timestamp` | ISO 8601 en UTC con milisegundos, del momento de la captura, no del envío |
  | `sessionId` | El de la sesión del navegador (§7): se crea al iniciar sesión; `null` en las vistas públicas |
  | `userId` | El usuario de la sesión, o `null` si no hay sesión |
  | `schemaVersion` | La del esquema de ese evento, tomada del catálogo generado desde `event-schemas.json` |
  | `requestId` | El `X-Request-Id` de la llamada a la API que confirma o rechaza el hecho; `null` si el evento no nace de una llamada |
  | `source` | `browser` |
  | `environment` | `NEXT_PUBLIC_TELEMETRY_ENVIRONMENT` (`development` si no está definida) |

- **Validación antes de emitir (§7.1).** `track()` comprueba cada evento contra un catálogo que un script genera desde `event-schemas.json`: el tipo debe existir, las propiedades obligatorias deben estar y no puede haber ninguna clave fuera del allowlist. Un evento que no cumple se descarta, con un aviso en la consola en desarrollo; nunca se recorta en silencio.
- **Correlación.** `lib/api-client.ts` crea un `X-Request-Id` por llamada. El BFF lo reenvía a la API, que lo escribe en su línea de `api.timing` y lo devuelve en la respuesta. Los eventos que nacen de una respuesta se emiten en la capa de datos, con el `requestId` de esa llamada.

### 13.2 Envío

| Mecanismo | Comportamiento |
|---|---|
| Cola local | Un arreglo en memoria. Como máximo 500 eventos: si el receptor no responde durante mucho tiempo, se descartan los más antiguos. |
| Lote | Se envía `{"events": [...]}` cada 10 segundos o al llegar a 20 eventos, lo que ocurra primero, a `NEXT_PUBLIC_TELEMETRY_ENDPOINT`. |
| Pestaña oculta o cerrada | En `visibilitychange` (`hidden`), lo pendiente sale con `navigator.sendBeacon`, en lotes de 20 como máximo. |
| Reintentos | Hasta 3, con esperas de 1, 2 y 4 segundos. Después se descarta el lote: la telemetría nunca bloquea la aplicación. Los reintentos conservan el `eventId`, para que el almacenamiento descarte duplicados. |

El receptor está en otro origen (la API, en el puerto 8000) y `sendBeacon` no puede enviar `application/json` a otro origen sin una comprobación previa de CORS. Por eso los lotes de `sendBeacon` van como `text/plain`, y el receptor interpreta el cuerpo como JSON en los dos casos.

### 13.3 Receptor provisional

> Sustituido por el receptor de la fase de almacenamiento (§14.3). Se conserva como registro de la fase de captura.

`POST /telemetry/events` en `services/brasaland-api`, en su propio router:

- **Fuera de `/api/v1` y público**, como `/health`. La recepción de telemetría es una vía de entrada aparte, no un recurso versionado del negocio, y `sendBeacon` no puede enviar `Authorization`.
- **CORS** solo para el origen del backoffice (`FRONTEND_URL`) y solo para `POST`.
- **Valida el formato** con el modelo `TelemetryEvent`: los 10 campos del envelope, con sus tipos y dominios y sin campos extra. Un lote tiene entre 1 y 100 eventos. `properties` se valida como objeto; la validación contra el esquema de cada evento llega con el almacenamiento.
- **Registra** en el log la cantidad de eventos y el `event_type` de cada uno, y responde `200 {"received": N}`. No escribe en ninguna base de datos.
- **`TELEMETRY_ENDPOINT`** queda declarada en la configuración de la API desde el principio, aunque todavía no se use.

### 13.4 Alcance: 34 de los 44 eventos

| Grupo | Eventos |
|---|---|
| **Obligatorios (6)** | `inbound_order_created`, `outbound_order_created`, `stock_waste_registered`, `stock_threshold_triggered`, `ingredient_price_variance_detected`, `direct_stock_edit_rejected` |
| Piso técnico (3) | `page_viewed`, `frontend_error_captured`, `page_performance_recorded` (Web Vitals: LCP, CLS e INP, agrupados por vista) |
| Autenticación (9) | `login_succeeded`, `login_failed`, `session_expired`, `auth_token_rejected`, `logout_completed`, `user_registered`, `password_reset_completed`, `password_reset_link_rejected`, `password_changed` |
| Inventario (2) | `order_validation_failed`, `outbound_order_rejected` |
| Errores y rendimiento de la API (3) | `api_error_returned`, `api_connection_failed`, `api_latency_recorded` (medidos en el navegador) |
| Navegación (4) | `form_validation_failed`, `form_abandoned`, `list_filter_applied`, `list_page_extended` |
| Proveedores (3) | `supplier_created`, `supplier_rate_updated`, `supplier_status_changed` |
| Incidencias (4) | `incident_created`, `incident_status_changed`, `incident_transition_rejected`, `incident_report_analyzed` |

**Esperan al emisor de la API (10):**

| Evento | Por qué no se captura en el backoffice |
|---|---|
| `product_created`, `user_access_changed`, `supplier_deleted` | El backoffice no tiene ningún control que haga esa operación. |
| `password_reset_requested` | Necesita saber si la cuenta existe y la huella del email, que solo tiene la API. |
| `server_error_occurred` | Necesita el tipo de la excepción, que la API no expone. |
| `cache_stats_recorded`, `email_delivery_failed`, `api_instance_started`, `data_seed_executed` | Solo existen dentro del servidor o de los scripts. |
| `incident_report_exported` | Falta la hora del análisis (brecha B13). |

### 13.5 Cambios de esquema de esta fase

- **26 eventos cambian de emisor** a `source: "browser"`. Su versión no cambia, porque sus propiedades son las mismas.
- **`login_failed` 2.0.0.** `failure_reason` admite también `network_error`, y salen `account_fingerprint` y `client_network`: el navegador no puede calcularlos sin enviar el email. Volverán con el emisor de la API.
- **`api_connection_failed` 1.1.0.** Admite `api_timeout` (504), que el intermediario ya devuelve.
- **Envelope:** `sessionId` se crea al iniciar sesión (§7).
- **Catálogo:** `urn:brasaland:telemetry:event-schemas:1.1.0`.

### 13.6 Dónde se captura cada evento

Ningún componente llama a `track()` por su cuenta: los eventos salen de la capa de datos (`lib/`), de los hooks compartidos o de un único componente en el layout raíz. Las rutas son relativas a `uis/backoffice/`.

| `event_type` | Clase | Dónde se captura | Cuándo |
|---|---|---|---|
| `inbound_order_created` | **Obligatorio** | `lib/inventory.ts` (`createEntry`) | 201 de la entrada |
| `ingredient_price_variance_detected` | **Obligatorio** | `lib/inventory.ts` (`createEntry`) | El coste se desvía más del 10 % de la media de 90 días (historial de `GET /inventory/orders`) |
| `outbound_order_created` | **Obligatorio** | `lib/inventory.ts` (`createExit`) | 201 de una salida de consumo |
| `stock_waste_registered` | **Obligatorio** | `lib/inventory.ts` (`createExit`) | 201 de una salida de merma |
| `stock_threshold_triggered` | **Obligatorio** | `lib/inventory.ts` (`createExit`) | La salida hace cruzar el umbral de stock bajo |
| `direct_stock_edit_rejected` | **Obligatorio** | `lib/api-client.ts` → `lib/telemetry/api-events.ts` | 405 de "Ajustar stock" (`components/inventario/StockAdjustModal.tsx`) o 422 por `current_stock` |
| `order_validation_failed` | Oportunidad | `lib/api-client.ts` → `api-events.ts` | 422 o 404 al registrar una orden |
| `outbound_order_rejected` | Oportunidad | `lib/inventory.ts` (`createExit`) | 400 `insufficient_stock` |
| `login_succeeded` | Oportunidad | `lib/auth/api.ts` (`login`) + `components/auth/SessionProvider.tsx` | Al validar la sesión tras un login (el rol llega con `/auth/me`) |
| `login_failed` | Oportunidad | `lib/auth/api.ts` (`login`) | 401, 403 `inactive_user` o la petición no llega a la API |
| `session_expired` | Oportunidad | `lib/api-client.ts` → `api-events.ts` | 401 `token_expired` |
| `auth_token_rejected` | Oportunidad | `lib/api-client.ts` → `api-events.ts` | 401 `invalid_token` o `session_revoked` |
| `logout_completed` | Oportunidad | `components/auth/SessionProvider.tsx` (`logout`) | "Cerrar sesión", antes de borrar el token |
| `user_registered` | Oportunidad | `lib/auth/api.ts` (`register`) | 201 de `POST /users` |
| `password_reset_completed` | Oportunidad | `lib/auth/api.ts` (`resetPassword`) | 200 del restablecimiento |
| `password_reset_link_rejected` | Oportunidad | `lib/api-client.ts` → `api-events.ts` | Enlace inválido, caducado o usado |
| `password_changed` | Oportunidad | `lib/auth/api.ts` (`changePassword`) | 200 del cambio de contraseña |
| `page_viewed` | Oportunidad | `components/telemetry/TelemetryRoot.tsx` (layout raíz) | Cada vista, la inicial y las navegaciones sin recarga |
| `form_validation_failed` | Oportunidad | `hooks/useFormTelemetry.ts` | La validación del navegador bloquea el envío (entrada, salida, incidencia, proveedor, login y registro) |
| `form_abandoned` | Oportunidad | `hooks/useFormTelemetry.ts` | Salir, cerrar el modal o cerrar la pestaña con el formulario empezado |
| `list_filter_applied` | Oportunidad | `hooks/useListFilterTelemetry.ts` | Cambio de filtro en el historial, el gestor o el directorio |
| `list_page_extended` | Oportunidad | `hooks/useShowMore.ts` | "Mostrar más" en el historial o el gestor |
| `api_latency_recorded` | Oportunidad | `lib/api-client.ts` → `api-events.ts` | Toda llamada con respuesta (muestreada) |
| `page_performance_recorded` | Oportunidad | `TelemetryRoot.tsx` (`useReportWebVitals`) → `lib/telemetry/performance.ts` | Al ocultar la pestaña, una vez por carga |
| `api_error_returned` | Oportunidad | `lib/api-client.ts` → `api-events.ts` | Cualquier 4xx |
| `frontend_error_captured` | Oportunidad | `TelemetryRoot.tsx` y `hooks/useReportBoundaryError.ts` (`error.tsx`, `global-error.tsx`) | `window.onerror`, `unhandledrejection` y las pantallas de error |
| `api_connection_failed` | Oportunidad | `lib/api-client.ts` → `api-events.ts` | 502, 504 o 500 del intermediario |
| `supplier_created` | Oportunidad | `lib/proveedores/api.ts` (`createSupplier`) | 201 del alta |
| `supplier_rate_updated` | Oportunidad | `lib/proveedores/api.ts` (`updateRate`) | 200 del cambio de tarifa |
| `supplier_status_changed` | Oportunidad | `lib/proveedores/api.ts` (`updateStatus`) | 200 del cambio de estado |
| `incident_created` | Oportunidad | `lib/gestor-incidencias/api.ts` (`createIncident`) | 201 del alta |
| `incident_status_changed` | Oportunidad | `lib/gestor-incidencias/api.ts` (`updateIncidentStatus`) | 200 del cambio de estado |
| `incident_transition_rejected` | Oportunidad | `lib/gestor-incidencias/api.ts` (`updateIncidentStatus`) | 400 `invalid_transition` |
| `incident_report_analyzed` | Oportunidad | `lib/incidencias/api.ts` (`analyzeIncidents`) | 200 del análisis |

**Verificación (2026-11-19):** en Chrome, con la API y `next dev` en local, la pestaña Network muestra los lotes `POST http://localhost:8000/telemetry/events` con el envelope completo y respuesta 200, también los enviados con `sendBeacon` al redirigir al login tras un 401. El receptor registra la cantidad y los `event_type` de cada lote.

## 14. Fase de almacenamiento

El receptor deja de ser provisional: valida cada evento por separado, guarda los válidos en la tabla `telemetry_events` de Supabase con una sola sentencia por lote y responde qué guardó y qué rechazó. La URL (`POST /telemetry/events`) y el formato del lote no cambian, así que el backoffice tampoco cambia.

### 14.1 La tabla `telemetry_events`

Solo admite inserciones: los eventos son hechos inmutables. Las columnas fijas sostienen las consultas analíticas; todo lo propio de cada evento va en `tags`, sin cambiar el esquema de la tabla cuando el catálogo crece.

| Columna | Tipo | Restricciones | Contenido |
|---|---|---|---|
| `id` | `uuid` | PK, default `gen_random_uuid()` | El `eventId` del envelope |
| `timestamp` | `timestamptz` | NOT NULL | Momento del hecho (del envelope), no el de la recepción |
| `service` | `text` | NOT NULL | Origen: `backoffice`, `api`, `bff` o `process` |
| `event_type` | `text` | NOT NULL | Tipo de evento (`entidad_acción`) |
| `level` | `text` | default `'info'` | `info`, `warn` o `error` |
| `value` | `numeric` | NULL | Métrica principal del evento, si tiene |
| `message` | `text` | NULL | Resumen legible, de 200 caracteres como máximo |
| `tags` | `jsonb` | default `'{}'` | `properties` del evento y cinco campos del envelope |

**Índices:** `idx_telemetry_events_timestamp` (`timestamp`), `idx_telemetry_events_event_type` (`event_type`) e `idx_telemetry_events_tags` (GIN sobre `tags`, para filtrar por dentro del JSON, por ejemplo `tags @> '{"country": "CO"}'`).

**Creación:** solo con `services/brasaland-api/migrations/002_telemetry_events.sql`, que se ejecuta una vez en Supabase y es idempotente. La API no crea esta tabla al arrancar: así no puede quedar una tabla sin índices ni protecciones. Si falta, el receptor responde 503 y el log indica qué migración ejecutar.

**Inmutabilidad:**

- El código de la API solo inserta en esta tabla: ningún `UPDATE` ni `DELETE`.
- En la base, un trigger rechaza cualquier `UPDATE`, `DELETE` o `TRUNCATE`, venga de donde venga (la consola de Supabase, un script).
- RLS está activado y sin políticas: la API REST que Supabase publica para el esquema `public` no puede leer ni escribir la tabla con la clave `anon`. La API se conecta como `postgres`, que no está sujeto a RLS.
- **Purgas excepcionales** (retención, derecho de supresión): se hacen a mano desactivando el trigger en una transacción y volviendo a activarlo. Es una operación consciente y documentada, nunca una ruta de la aplicación.

### 14.2 De un evento a una fila

| Columna | Origen |
|---|---|
| `id` | `eventId` |
| `timestamp` | `timestamp` |
| `service` | `source`: `browser` → `backoffice`; `api`, `bff` y `process` se guardan igual |
| `event_type` | `event_type` |
| `level` | `x-level` del esquema del evento (fijo por tipo) |
| `value` | La propiedad que indica `x-value` del esquema; NULL si el evento no tiene o si llega `null` |
| `message` | La plantilla `x-message` del esquema, con sus huecos `{propiedad}` rellenos |
| `tags` | `properties` tal cual, más `session_id`, `user_id`, `request_id`, `schema_version` y `environment` del envelope |

- **`level`.** `error` cuando algo falló: `frontend_error_captured`, `api_connection_failed`, `server_error_occurred` y `email_delivery_failed`. `warn` en los rechazos y alertas que alguien debería mirar: `direct_stock_edit_rejected`, `stock_threshold_triggered`, `ingredient_price_variance_detected`, `outbound_order_rejected`, `order_validation_failed`, `login_failed`, `auth_token_rejected`, `password_reset_link_rejected`, `api_error_returned`, `incident_transition_rejected` y `form_validation_failed`. `info` en el resto, incluido `session_expired`, que es el final normal de una sesión.
- **`value`.** Cada evento declara como mucho una propiedad numérica principal (la cantidad en el inventario, la duración en el rendimiento, el porcentaje en las variaciones de precio y tarifa…). El número se copia y sigue también en `tags`. **No tiene unidad propia:** la unidad la da el `event_type` (kg o unidades, ms, %, minutos), así que las consultas siempre filtran por tipo y nunca suman `value` de tipos distintos.
- **`message`.** Plantilla en español por evento, por ejemplo `Merma de {quantity} {unit} de {product_id} en {location_id} ({reason})`. Solo usa claves del allowlist del evento, que ya está libre de datos personales (§8). Un hueco sin valor se escribe `—`, los booleanos como `sí` o `no` y las listas separadas por comas.
- **`tags`.** Guarda las dimensiones de Brasaland tal como las emite cada evento (`location_id`, `country`, `product_id`, `product_category`, `supplier_id`, `currency`, `reason`, `branch`…), para agregar por local, por país y por semana. Los cinco campos del envelope van en snake_case y siempre están, con `null` si no hay valor. `eventId` y `source` no se repiten: ya son `id` y `service`. Ninguna propiedad del catálogo usa esos cinco nombres.

Las fichas (sección 15) muestran el `level`, el `value` y la plantilla de cada evento.

### 14.3 El receptor

`POST /telemetry/events` lee el lote de forma laxa y valida **cada evento por separado**, para que un evento malo no tumbe a los demás:

1. **El lote.** El cuerpo debe ser un objeto JSON con una lista `events` (las demás claves se ignoran). Si no lo es, responde 422; si pasa de 256 KB, 413 `batch_too_large`; si trae más de 100 eventos, 422 `too_many_events`. `events: []` responde con ceros sin tocar la base.
2. **El envelope.** Cada elemento se valida con `TelemetryEvent.model_validate`, el mismo modelo de la fase de captura, sin cambios.
3. **Las propiedades.** Después, contra el catálogo de la API, que un script genera desde `event-schemas.json` (como el del backoffice): el `event_type` debe existir, las propiedades obligatorias deben estar y no puede haber claves fuera del allowlist. Así `tags` nunca guarda lo que el plan no permite, aunque el lote no venga del backoffice.
4. **El guardado.** Los eventos válidos se insertan con **una sola sentencia** (`INSERT … VALUES (…), (…) ON CONFLICT (id) DO NOTHING`), en una transacción. Un evento repetido, por un reintento o un `sendBeacon` que llegó dos veces, no crea otra fila.
5. **La respuesta.** `200 {"received": N, "stored": M, "rejected": R}`, con `N = M + R`. Los repetidos cuentan en `stored`, porque ya están guardados. El backoffice solo mira el código de estado.

**Si la base no responde**, el receptor no guarda nada y responde 503 `telemetry_storage_unavailable`. El backoffice reintenta los 5xx con su backoff (§13.2), y el `ON CONFLICT` hace seguros los reintentos.

**Log.** Una línea por lote en `api.telemetry` con los recibidos, guardados, repetidos y rechazados. De cada rechazo se anota la posición, el `event_type` (si lo trae) y el primer campo que falló, **nunca su valor**, para que un lote malicioso no meta datos personales en los logs.

### 14.4 Cambios de esquema de esta fase

- **Catálogo 1.2.0** (`urn:brasaland:telemetry:event-schemas:1.2.0`): cada evento lleva `x-level`, `x-value` y `x-message`. Son anotaciones: no cambian qué eventos son válidos, así que ninguna versión de evento cambia y el backoffice no se toca.
- **R2 y R4** (§11.3) se ajustan a la tabla inmutable de ocho columnas.

### 14.5 Verificación

**2026-11-19**, con la API en local contra Supabase y `next dev`, sin cambios en el backoffice:

- **Eventos reales.** Desde el backoffice se registraron una entrada (`inbound_order_created`), una salida por merma (`stock_waste_registered`), un login fallido y otro correcto, y un "Ajustar stock" (`direct_stock_edit_rejected`), además de las vistas, las latencias y los formularios abandonados que se generan solos. Los 13 lotes del backoffice respondieron 200, sin ningún rechazo. En `telemetry_events` aparecen con `service`, `level`, `value`, `message` y `tags`; `tags` conserva las dimensiones del briefing (`location_id`, `country`, `product_id`, `product_category`, `quantity`, `unit`, `currency`, `supplier_id`, `reason`) y los cinco campos del envelope.
- **Rechazo parcial.** Un lote enviado con curl con 2 eventos válidos y 5 inválidos (timestamp mal formado, clave fuera del allowlist, tipo fuera del catálogo, campo del envelope ausente y un elemento que no es un objeto) respondió `200 {"received": 7, "stored": 2, "rejected": 5}`; el log nombra cada rechazo sin copiar sus valores.

## 15. Fichas de los eventos

Una ficha por evento, en el mismo orden y con las mismas propiedades que `event-schemas.json`. **El allowlist de cada evento son exactamente las propiedades de su tabla:** cualquier otra clave hace que el evento no se emita. "Obligatoria: sí" significa que la clave debe estar siempre; las opcionales se omiten cuando no hay valor.

### Inventario

#### `inbound_order_created`

Un local registra la llegada de mercancía de un proveedor.

| | |
|---|---|
| **Clasificación** | Obligatorio |
| **Versión** | `1.0.0` |
| **Emisor** | Navegador (`source: browser`) |
| **Se emite** | En el backoffice, al recibir el 201 de `POST /api/v1/inventory/orders/inbound` (la entrada ya está guardada). `supplier_id` sale del directorio por el nombre elegido; `country` y `currency`, del ingrediente. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador: se crea al iniciar sesión; `null` en las vistas públicas (antes del login). |
| **`requestId`** | Id de la llamada a la API que confirma o rechaza el hecho (`X-Request-Id`, creado por `lib/api-client.ts`). |
| **Datos sensibles** | Ninguno. Describe productos y locales, no personas. |
| **Entrega** | **batch** (diario (cierre 02:00 hora local)). Consolidar compras y negociar precios son decisiones semanales o mensuales de Lucía; nadie actúa sobre una entrega concreta en minutos. |
| **Throttle / debounce** | No necesita: su frecuencia es la de una acción humana o de negocio. |
| **Almacenamiento** | `level`: `info`; `value`: `quantity`; `message`: `Entrada de {quantity} {unit} de {product_id} en {location_id} (proveedor {supplier_id}, {unit_cost} {currency})` |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `order_id` | integer (≥ 1) | sí | Id de la orden registrada. |
| `location_id` | integer (1–14) | sí | Local (1–14) donde ocurre el hecho. |
| `country` | enum: `CO`, `US` | sí | País del local: `CO` (Colombia) o `US` (Florida). Nunca el idioma de la interfaz. |
| `product_id` | integer (≥ 1) | sí | Id del producto (hoy `Ingredient.id`). |
| `product_category` | enum: `proteína`, `vegetal`, `salsa`, `bebida`, `empaque`, `limpieza` | sí | Categoría del producto, con los valores del briefing (hoy `meat`→`proteína`, `produce`→`vegetal`, `sauce`→`salsa`, `beverage`→`bebida`, `packaging`→`empaque`, `cleaning`→`limpieza`). |
| `quantity` | number (> 0) | sí | Cantidad de la orden, en `unit`. |
| `unit` | enum: `kg`, `unidad`, `litro` | sí | Unidad de medida del producto. |
| `currency` | enum: `COP`, `USD` | sí | Moneda del local (`COP` en Colombia, `USD` en Florida). Sin conversión. |
| `supplier_id` | integer (≥ 1) | sí | Id del proveedor en el directorio. |
| `unit_cost` | number (> 0) | sí | Coste por unidad de la entrega, en `currency`. |

#### `outbound_order_created`

Un local registra consumo de ingredientes en la preparación de un plato.

| | |
|---|---|
| **Clasificación** | Obligatorio |
| **Versión** | `1.0.0` |
| **Emisor** | Navegador (`source: browser`) |
| **Se emite** | Al recibir el 201 de `POST /api/v1/inventory/orders/outbound` con motivo de consumo. Una salida de merma emite `stock_waste_registered` en su lugar. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador: se crea al iniciar sesión; `null` en las vistas públicas (antes del login). |
| **`requestId`** | Id de la llamada a la API que confirma o rechaza el hecho (`X-Request-Id`, creado por `lib/api-client.ts`). |
| **Datos sensibles** | Ninguno. Describe productos y locales, no personas. |
| **Entrega** | **batch** (diario (cierre 02:00 hora local)). La sugerencia automática de pedidos se recalcula con el consumo acumulado del día; un consumo concreto no cambia la decisión en minutos. |
| **Throttle / debounce** | No necesita: su frecuencia es la de una acción humana o de negocio. |
| **Almacenamiento** | `level`: `info`; `value`: `quantity`; `message`: `Consumo de {quantity} {unit} de {product_id} en {location_id}; quedan {stock_after} {unit}` |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `order_id` | integer (≥ 1) | sí | Id de la orden registrada. |
| `location_id` | integer (1–14) | sí | Local (1–14) donde ocurre el hecho. |
| `country` | enum: `CO`, `US` | sí | País del local: `CO` (Colombia) o `US` (Florida). Nunca el idioma de la interfaz. |
| `product_id` | integer (≥ 1) | sí | Id del producto (hoy `Ingredient.id`). |
| `product_category` | enum: `proteína`, `vegetal`, `salsa`, `bebida`, `empaque`, `limpieza` | sí | Categoría del producto, con los valores del briefing (hoy `meat`→`proteína`, `produce`→`vegetal`, `sauce`→`salsa`, `beverage`→`bebida`, `packaging`→`empaque`, `cleaning`→`limpieza`). |
| `quantity` | number (> 0) | sí | Cantidad de la orden, en `unit`. |
| `unit` | enum: `kg`, `unidad`, `litro` | sí | Unidad de medida del producto. |
| `currency` | enum: `COP`, `USD` | sí | Moneda del local (`COP` en Colombia, `USD` en Florida). Sin conversión. |
| `stock_after` | number (≥ 0) | no | Stock del producto tras la salida, en `unit`. |

#### `stock_waste_registered`

Un local registra merma (producto vencido, error de cocina, o pérdida/robo).

| | |
|---|---|
| **Clasificación** | Obligatorio |
| **Versión** | `1.0.0` |
| **Emisor** | Navegador (`source: browser`) |
| **Se emite** | Al recibir el 201 de `POST /api/v1/inventory/orders/outbound` con motivo de merma; `reason` es el `waste_reason` de la salida. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador: se crea al iniciar sesión; `null` en las vistas públicas (antes del login). |
| **`requestId`** | Id de la llamada a la API que confirma o rechaza el hecho (`X-Request-Id`, creado por `lib/api-client.ts`). |
| **Datos sensibles** | Ninguno. Describe productos y locales, no personas. |
| **Entrega** | **batch** (diario (cierre 02:00 hora local)). Priorizar auditorías de merma es una decisión semanal por local; la merma de hoy ya ocurrió y no se corrige en minutos. |
| **Throttle / debounce** | No necesita: su frecuencia es la de una acción humana o de negocio. |
| **Almacenamiento** | `level`: `info`; `value`: `quantity`; `message`: `Merma de {quantity} {unit} de {product_id} en {location_id} ({reason})` |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `order_id` | integer (≥ 1) | sí | Id de la orden registrada. |
| `location_id` | integer (1–14) | sí | Local (1–14) donde ocurre el hecho. |
| `country` | enum: `CO`, `US` | sí | País del local: `CO` (Colombia) o `US` (Florida). Nunca el idioma de la interfaz. |
| `product_id` | integer (≥ 1) | sí | Id del producto (hoy `Ingredient.id`). |
| `product_category` | enum: `proteína`, `vegetal`, `salsa`, `bebida`, `empaque`, `limpieza` | sí | Categoría del producto, con los valores del briefing (hoy `meat`→`proteína`, `produce`→`vegetal`, `sauce`→`salsa`, `beverage`→`bebida`, `packaging`→`empaque`, `cleaning`→`limpieza`). |
| `quantity` | number (> 0) | sí | Cantidad de la orden, en `unit`. |
| `unit` | enum: `kg`, `unidad`, `litro` | sí | Unidad de medida del producto. |
| `currency` | enum: `COP`, `USD` | sí | Moneda del local (`COP` en Colombia, `USD` en Florida). Sin conversión. |
| `reason` | enum: `expired`, `kitchen_error`, `theft_suspected` | sí | Motivo de la merma, con los valores del briefing. |
| `stock_after` | number (≥ 0) | no | Stock del producto tras la merma, en `unit`. |

#### `stock_threshold_triggered`

El stock de un producto cae por debajo del mínimo configurado para ese local.

| | |
|---|---|
| **Clasificación** | Obligatorio |
| **Versión** | `1.0.0` |
| **Emisor** | Navegador (`source: browser`) |
| **Se emite** | Al recibir el 201 de una salida que hace cruzar el mínimo: stock antes ≥ `threshold_quantity` y después < `threshold_quantity`. Mientras no haya mínimos por local (brecha B3), el mínimo es el umbral de stock bajo del backoffice para la unidad del producto (`LOW_STOCK_THRESHOLDS`) y el stock es el global del producto. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador: se crea al iniciar sesión; `null` en las vistas públicas (antes del login). |
| **`requestId`** | Id de la llamada a la API que confirma o rechaza el hecho (`X-Request-Id`, creado por `lib/api-client.ts`). |
| **Datos sensibles** | Ninguno. Describe productos y locales, no personas. |
| **Entrega** | **stream** (segundos). Un local que se queda corto de un ingrediente clave necesita reponer **ese mismo día**: el supervisor debe enterarse en minutos, no al día siguiente. Además alimenta en batch el ajuste del mínimo. |
| **Throttle / debounce** | Natural: solo se emite al **cruzar** el mínimo (§3.2), así que un producto bajo no repite la alerta en cada consumo. |
| **Almacenamiento** | `level`: `warn`; `value`: `quantity`; `message`: `Stock bajo de {product_id}: {quantity} {unit}, por debajo del mínimo de {threshold_quantity} {unit}` |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `location_id` | integer (1–14) | sí | Local (1–14) donde ocurre el hecho. |
| `country` | enum: `CO`, `US` | sí | País del local: `CO` (Colombia) o `US` (Florida). Nunca el idioma de la interfaz. |
| `product_id` | integer (≥ 1) | sí | Id del producto (hoy `Ingredient.id`). |
| `product_category` | enum: `proteína`, `vegetal`, `salsa`, `bebida`, `empaque`, `limpieza` | sí | Categoría del producto, con los valores del briefing (hoy `meat`→`proteína`, `produce`→`vegetal`, `sauce`→`salsa`, `beverage`→`bebida`, `packaging`→`empaque`, `cleaning`→`limpieza`). |
| `quantity` | number (≥ 0) | sí | Stock resultante tras la salida que cruzó el mínimo, en `unit`. |
| `unit` | enum: `kg`, `unidad`, `litro` | sí | Unidad de medida del producto. |
| `currency` | enum: `COP`, `USD` | sí | Moneda del local (`COP` en Colombia, `USD` en Florida). Sin conversión. |
| `threshold_quantity` | number (> 0) | sí | Mínimo configurado para ese producto y local, en `unit`. |
| `trigger_order_id` | integer (≥ 1) | sí | Id de la salida que provocó el cruce. |

#### `direct_stock_edit_rejected`

Un usuario intenta modificar el stock directamente (fuera de una orden) y el sistema lo rechaza.

| | |
|---|---|
| **Clasificación** | Obligatorio |
| **Versión** | `1.0.0` |
| **Emisor** | Navegador (`source: browser`) |
| **Se emite** | En `lib/api-client.ts`, al recibir 405 a un `PUT`/`PATCH`/`DELETE` sobre una ruta del inventario, o 422 con `extra_forbidden` en `current_stock` o `stock` a un `POST` del inventario. Desde la interfaz lo provoca la acción "Ajustar stock" de `/inventario/ingredientes`. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador: se crea al iniciar sesión; `null` en las vistas públicas (antes del login). |
| **`requestId`** | Id de la llamada a la API que confirma o rechaza el hecho (`X-Request-Id`, creado por `lib/api-client.ts`). |
| **Datos sensibles** | Ninguno. No se guarda el cuerpo de la petición ni el valor de stock que se intentó escribir. |
| **Entrega** | **batch** (diario (cierre 02:00 hora local)). Reforzar capacitación o permisos es una decisión semanal de Jake; el sistema ya rechazó el intento, no hay daño que contener en minutos. |
| **Throttle / debounce** | No necesita: su frecuencia es la de una acción humana o de negocio. |
| **Almacenamiento** | `level`: `warn`; `value`: `quantity`; `message`: `Edición directa del stock rechazada: {method} {route} → {status_code} (rol {user_role})` |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `location_id` | integer (1–14) | no | Local, si la petición lo indica (cuerpo de una orden). Una edición sobre `/products/{id}` no lleva local. |
| `country` | enum: `CO`, `US` | no | País del producto, si se identifica uno. |
| `product_id` | integer (≥ 1) | no | Producto, si la ruta o el cuerpo lo identifican. |
| `product_category` | enum: `proteína`, `vegetal`, `salsa`, `bebida`, `empaque`, `limpieza` | no | Categoría del producto, con los valores del briefing (hoy `meat`→`proteína`, `produce`→`vegetal`, `sauce`→`salsa`, `beverage`→`bebida`, `packaging`→`empaque`, `cleaning`→`limpieza`). |
| `quantity` | number (> 0) | no | Cantidad de la orden, si la petición era una orden. |
| `unit` | enum: `kg`, `unidad`, `litro` | no | Unidad de medida del producto. |
| `currency` | enum: `COP`, `USD` | no | Moneda del local, si se conoce el local. |
| `method` | enum: `GET`, `POST`, `PUT`, `PATCH`, `DELETE` | sí | Método HTTP. |
| `route` | string | sí | Plantilla de la ruta, nunca la URL real: `/api/v1/inventory/products/{ingredient_id}` en la API, `/talento/candidates/[id]` en el backoffice. Sin query string. |
| `rejection_type` | enum: `method_not_allowed`, `forbidden_field` | sí | `method_not_allowed` (405) o `forbidden_field` (422 por un campo de stock en el cuerpo). |
| `status_code` | enum: `405`, `422` | sí | 405 o 422. |
| `user_role` | enum: `admin`, `manager`, `user` | sí | Rol de la cuenta. |

#### `ingredient_price_variance_detected`

El costo unitario de una orden de entrada varía más de un umbral (ej. 10%) respecto al histórico del mismo producto/proveedor.

| | |
|---|---|
| **Clasificación** | Obligatorio |
| **Versión** | `1.0.0` |
| **Emisor** | Navegador (`source: browser`) |
| **Se emite** | Al recibir el 201 de una entrada cuyo `unit_cost` se desvía más de `threshold_pct` de la media de las entradas de los últimos `history_window_days` días del mismo producto y proveedor (al menos 3), calculada con el historial de `GET /api/v1/inventory/orders`. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador: se crea al iniciar sesión; `null` en las vistas públicas (antes del login). |
| **`requestId`** | Id de la llamada a la API que confirma o rechaza el hecho (`X-Request-Id`, creado por `lib/api-client.ts`). |
| **Datos sensibles** | Ninguno. Describe productos y locales, no personas. |
| **Entrega** | **stream** (segundos). Es una alerta para Lucía y Mariana: renegociar o cambiar de proveedor **antes** de aceptar más entregas al precio nuevo. Un día de retraso son más compras al precio anómalo. |
| **Throttle / debounce** | No necesita: su frecuencia es la de una acción humana o de negocio. |
| **Almacenamiento** | `level`: `warn`; `value`: `variance_pct`; `message`: `Coste de {product_id} del proveedor {supplier_id}: {unit_cost} {currency}, {variance_pct} % frente a la media de {historical_avg_unit_cost}` |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `order_id` | integer (≥ 1) | sí | Id de la orden registrada. |
| `location_id` | integer (1–14) | sí | Local (1–14) donde ocurre el hecho. |
| `country` | enum: `CO`, `US` | sí | País del local: `CO` (Colombia) o `US` (Florida). Nunca el idioma de la interfaz. |
| `product_id` | integer (≥ 1) | sí | Id del producto (hoy `Ingredient.id`). |
| `product_category` | enum: `proteína`, `vegetal`, `salsa`, `bebida`, `empaque`, `limpieza` | sí | Categoría del producto, con los valores del briefing (hoy `meat`→`proteína`, `produce`→`vegetal`, `sauce`→`salsa`, `beverage`→`bebida`, `packaging`→`empaque`, `cleaning`→`limpieza`). |
| `quantity` | number (> 0) | sí | Cantidad de la orden, en `unit`. |
| `unit` | enum: `kg`, `unidad`, `litro` | sí | Unidad de medida del producto. |
| `currency` | enum: `COP`, `USD` | sí | Moneda del local (`COP` en Colombia, `USD` en Florida). Sin conversión. |
| `supplier_id` | integer (≥ 1) | sí | Id del proveedor en el directorio. |
| `unit_cost` | number (> 0) | sí | Coste por unidad de la entrega, en `currency`. |
| `historical_avg_unit_cost` | number (> 0) | sí | Media del coste unitario en la ventana, en `currency`. |
| `variance_pct` | number | sí | Desviación en porcentaje: (unit_cost − media) / media × 100. Positiva si sube. |
| `threshold_pct` | number (> 0) | sí | Umbral configurado, en porcentaje (10 por defecto). |
| `history_window_days` | integer (≥ 1) | sí | Días de histórico usados (90 por defecto). |
| `history_sample_size` | integer (≥ 3) | sí | Entradas del histórico usadas para la media (≥ 3). |

#### `order_validation_failed`

La API rechaza una orden de entrada o de salida por datos inválidos.

| | |
|---|---|
| **Clasificación** | Oportunidad identificada |
| **Versión** | `1.0.0` |
| **Emisor** | Navegador (`source: browser`) |
| **Se emite** | Al recibir 422 `invalid_request` o 404 `ingredient_not_found` de `POST /api/v1/inventory/orders/inbound` u `/outbound`. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador: se crea al iniciar sesión; `null` en las vistas públicas (antes del login). |
| **`requestId`** | Id de la llamada a la API que confirma o rechaza el hecho (`X-Request-Id`, creado por `lib/api-client.ts`). |
| **Datos sensibles** | Ninguno. Solo nombres de campo, nunca los valores enviados. |
| **Entrega** | **batch** (diario (cierre 02:00 hora local)). Corregir datos de catálogo y capacitar se decide con el acumulado de la semana. |
| **Throttle / debounce** | No necesita: su frecuencia es la de una acción humana o de negocio. |
| **Almacenamiento** | `level`: `warn`; `value`: NULL; `message`: `Orden de {order_type} rechazada: {error_code} ({status_code})` |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `order_type` | enum: `inbound`, `outbound` | sí | Tipo de orden. |
| `product_id` | integer (≥ 1) | no | Producto, si el cuerpo trae un `ingredient_id` legible. |
| `location_id` | integer (1–14) | no | Local, si el cuerpo trae un `location_id` válido. |
| `error_code` | enum: `invalid_request`, `ingredient_not_found` | sí | Código de la respuesta. |
| `invalid_fields` | array de string | sí | Campos señalados en `details` (vacío en un 404). |
| `status_code` | enum: `404`, `422` | sí | 422 o 404. |

#### `outbound_order_rejected`

La API rechaza una salida porque supera el stock disponible.

| | |
|---|---|
| **Clasificación** | Oportunidad identificada |
| **Versión** | `1.0.0` |
| **Emisor** | Navegador (`source: browser`) |
| **Se emite** | Al recibir 400 `insufficient_stock` de `POST /api/v1/inventory/orders/outbound` (no se escribió nada). `available_quantity` es el stock que mostraba el formulario. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador: se crea al iniciar sesión; `null` en las vistas públicas (antes del login). |
| **`requestId`** | Id de la llamada a la API que confirma o rechaza el hecho (`X-Request-Id`, creado por `lib/api-client.ts`). |
| **Datos sensibles** | Ninguno. Describe productos y locales, no personas. |
| **Entrega** | **batch** (diario (cierre 02:00 hora local)). El conteo físico se programa con el acumulado del día por producto y local; el rechazo ya protegió el stock. |
| **Throttle / debounce** | No necesita: su frecuencia es la de una acción humana o de negocio. |
| **Almacenamiento** | `level`: `warn`; `value`: `quantity`; `message`: `Salida de {quantity} {unit} de {product_id} rechazada: solo hay {available_quantity} {unit}` |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `location_id` | integer (1–14) | sí | Local (1–14) donde ocurre el hecho. |
| `country` | enum: `CO`, `US` | sí | País del local: `CO` (Colombia) o `US` (Florida). Nunca el idioma de la interfaz. |
| `product_id` | integer (≥ 1) | sí | Id del producto (hoy `Ingredient.id`). |
| `product_category` | enum: `proteína`, `vegetal`, `salsa`, `bebida`, `empaque`, `limpieza` | sí | Categoría del producto, con los valores del briefing (hoy `meat`→`proteína`, `produce`→`vegetal`, `sauce`→`salsa`, `beverage`→`bebida`, `packaging`→`empaque`, `cleaning`→`limpieza`). |
| `quantity` | number (> 0) | sí | Cantidad que se intentó sacar, en `unit`. |
| `unit` | enum: `kg`, `unidad`, `litro` | sí | Unidad de medida del producto. |
| `currency` | enum: `COP`, `USD` | sí | Moneda del local (`COP` en Colombia, `USD` en Florida). Sin conversión. |
| `available_quantity` | number (≥ 0) | sí | Stock disponible en ese momento, en `unit`. |
| `outbound_type` | enum: `consumption`, `waste` | sí | Tipo de salida intentada. |

#### `product_created`

Se da de alta un producto en el catálogo de inventario.

| | |
|---|---|
| **Clasificación** | Oportunidad identificada |
| **Versión** | `1.0.0` |
| **Emisor** | API (`source: api`) |
| **Se emite** | Tras el `commit` de `POST /api/v1/inventory/products`. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador (cabecera `X-Session-Id`); `null` si la petición no viene del backoffice. |
| **`requestId`** | Id de la petición (`X-Request-Id`). |
| **Datos sensibles** | Ninguno. El nombre de un ingrediente no es un dato personal. |
| **Entrega** | **batch** (diario (cierre 02:00 hora local)). Revisar duplicados del catálogo es una tarea periódica de Compras. |
| **Throttle / debounce** | No necesita: su frecuencia es la de una acción humana o de negocio. |
| **Almacenamiento** | `level`: `info`; `value`: NULL; `message`: `Ingrediente {product_id} creado ({product_category}, {unit}, {country})` |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `product_id` | integer (≥ 1) | sí | Id del producto (hoy `Ingredient.id`). |
| `product_category` | enum: `proteína`, `vegetal`, `salsa`, `bebida`, `empaque`, `limpieza` | sí | Categoría del producto, con los valores del briefing (hoy `meat`→`proteína`, `produce`→`vegetal`, `sauce`→`salsa`, `beverage`→`bebida`, `packaging`→`empaque`, `cleaning`→`limpieza`). |
| `country` | enum: `CO`, `US` | sí | País del local: `CO` (Colombia) o `US` (Florida). Nunca el idioma de la interfaz. |
| `unit` | enum: `kg`, `unidad`, `litro` | sí | Unidad de medida del producto. |
| `product_name` | string (máx. 120) | sí | Nombre del producto, para detectar duplicados. |

### Autenticación y sesión

#### `login_succeeded`

Un usuario inicia sesión.

| | |
|---|---|
| **Clasificación** | Oportunidad identificada |
| **Versión** | `1.0.0` |
| **Emisor** | Navegador (`source: browser`) |
| **Se emite** | En el formulario de login, al recibir el token de `POST /api/v1/auth/login` y validar la sesión con `GET /api/v1/auth/me`, de donde sale `user_role`. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador: se crea al iniciar sesión; `null` en las vistas públicas (antes del login). |
| **`requestId`** | Id de la llamada a la API que confirma o rechaza el hecho (`X-Request-Id`, creado por `lib/api-client.ts`). |
| **Datos sensibles** | `userId` es un identificador seudónimo (UUID). No se guarda el email. |
| **Entrega** | **batch** (diario (cierre 02:00 hora local)). Planificar capacitación y ventanas de mantenimiento usa patrones de semanas. |
| **Throttle / debounce** | No necesita: su frecuencia es la de una acción humana o de negocio. |
| **Almacenamiento** | `level`: `info`; `value`: NULL; `message`: `Inicio de sesión ({user_role})` |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `user_role` | enum: `admin`, `manager`, `user` | sí | Rol de la cuenta. |

#### `login_failed`

Un intento de inicio de sesión falla.

| | |
|---|---|
| **Clasificación** | Oportunidad identificada |
| **Versión** | `2.0.0` |
| **Emisor** | Navegador (`source: browser`) |
| **Se emite** | En el formulario de login, al recibir 401 `invalid_credentials` o 403 `inactive_user` de `POST /api/v1/auth/login`, o cuando la petición no llega a la API (`network_error`: fallo de red, o 502/504 del intermediario). |
| **`userId`** | `null`: la petición no está autenticada. |
| **`sessionId`** | Sesión del navegador: se crea al iniciar sesión; `null` en las vistas públicas (antes del login). |
| **`requestId`** | Id de la llamada a la API que confirma o rechaza el hecho (`X-Request-Id`, creado por `lib/api-client.ts`). |
| **Datos sensibles** | Ninguno. El email y la contraseña escritos nunca se emiten, ni nada derivado de ellos. `userId` es `null` aunque la cuenta exista. La huella de la cuenta (`account_fingerprint`) y la red (`client_network`) salen en la 2.0.0: el navegador no puede calcularlas sin enviar el email; vuelven con el emisor de la API. |
| **Entrega** | **stream** (segundos). Un ataque de fuerza bruta se detiene en minutos o no se detiene: la decisión (bloqueo temporal) solo sirve si llega a tiempo. |
| **Throttle / debounce** | Sin muestreo ni límite: cada intento cuenta para detectar la ráfaga. En el navegador, su frecuencia es la de los envíos del formulario de login. |
| **Almacenamiento** | `level`: `warn`; `value`: NULL; `message`: `Inicio de sesión fallido ({failure_reason})` |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `failure_reason` | enum: `invalid_credentials`, `inactive_user`, `network_error` | sí | Motivo: credenciales incorrectas, cuenta inactiva o petición que no llegó a la API. |

#### `session_expired`

Una petición llega con una sesión caducada.

| | |
|---|---|
| **Clasificación** | Oportunidad identificada |
| **Versión** | `1.0.0` |
| **Emisor** | Navegador (`source: browser`) |
| **Se emite** | En `lib/api-client.ts` (también al validar la sesión en `SessionProvider`), al recibir 401 `token_expired`. `token_age_minutes` sale del `iat` del token, leído sin verificar la firma. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador: se crea al iniciar sesión; `null` en las vistas públicas (antes del login). |
| **`requestId`** | Id de la llamada a la API que confirma o rechaza el hecho (`X-Request-Id`, creado por `lib/api-client.ts`). |
| **Datos sensibles** | `userId` es el de la sesión del navegador. No se emite el token. |
| **Entrega** | **batch** (diario (cierre 02:00 hora local)). Ajustar la duración del token es una decisión de configuración que se toma con semanas de datos. |
| **Throttle / debounce** | Uno por token: varias peticiones en paralelo con el mismo token caducado (resumen y listado) emiten un solo evento por (`userId`, `iat`) en 60 s. |
| **Almacenamiento** | `level`: `info`; `value`: `token_age_minutes`; `message`: `Sesión caducada en {route} tras {token_age_minutes} min` |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `route` | string | sí | Plantilla de la ruta, nunca la URL real: `/api/v1/inventory/products/{ingredient_id}` en la API, `/talento/candidates/[id]` en el backoffice. Sin query string. |
| `token_age_minutes` | integer (≥ 0) | sí | Minutos desde la emisión del token (`iat`). |

#### `auth_token_rejected`

Una petición llega con un token inválido o revocado.

| | |
|---|---|
| **Clasificación** | Oportunidad identificada |
| **Versión** | `1.0.0` |
| **Emisor** | Navegador (`source: browser`) |
| **Se emite** | En `lib/api-client.ts` (también al validar la sesión en `SessionProvider`), al recibir 401 `invalid_token` o `session_revoked`. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador: se crea al iniciar sesión; `null` en las vistas públicas (antes del login). |
| **`requestId`** | Id de la llamada a la API que confirma o rechaza el hecho (`X-Request-Id`, creado por `lib/api-client.ts`). |
| **Datos sensibles** | `userId` es el de la sesión del navegador, si la había. No se emite el token. |
| **Entrega** | **stream** (segundos). Tokens manipulados o sesiones revocadas que insisten son un posible incidente de seguridad: investigar y rotar `SECRET_KEY` no puede esperar al día siguiente. |
| **Throttle / debounce** | Uno por token y motivo cada 60 s (las peticiones en paralelo comparten token). |
| **Almacenamiento** | `level`: `warn`; `value`: NULL; `message`: `Token rechazado en {route} ({rejection_reason})` |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `rejection_reason` | enum: `invalid_token`, `session_revoked` | sí | Motivo del rechazo. |
| `route` | string | sí | Plantilla de la ruta, nunca la URL real: `/api/v1/inventory/products/{ingredient_id}` en la API, `/talento/candidates/[id]` en el backoffice. Sin query string. |

#### `logout_completed`

El usuario cierra sesión.

| | |
|---|---|
| **Clasificación** | Oportunidad identificada |
| **Versión** | `1.0.0` |
| **Emisor** | Navegador (`source: browser`) |
| **Se emite** | Al pulsar "Cerrar sesión" en el menú de la cuenta, antes de borrar el token. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador: se crea al iniciar sesión; `null` en las vistas públicas (antes del login). |
| **`requestId`** | `null`: no hay petición a la API. |
| **Datos sensibles** | Ninguno. |
| **Entrega** | **batch** (diario (cierre 02:00 hora local)). El cierre automático por inactividad se decide con el patrón de semanas. |
| **Throttle / debounce** | No necesita: su frecuencia es la de una acción humana o de negocio. |
| **Almacenamiento** | `level`: `info`; `value`: `session_duration_seconds`; `message`: `Cierre de sesión tras {session_duration_seconds} s` |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `route` | string | sí | Vista desde la que se cerró la sesión. |
| `session_duration_seconds` | integer (≥ 0) | sí | Segundos desde el inicio de la sesión del navegador. |

#### `user_registered`

Se crea una cuenta por autorregistro.

| | |
|---|---|
| **Clasificación** | Oportunidad identificada |
| **Versión** | `1.0.0` |
| **Emisor** | Navegador (`source: browser`) |
| **Se emite** | En el formulario de registro, al recibir el 201 de `POST /api/v1/users`; `new_user_id` es el `id` de la respuesta. |
| **`userId`** | `null`: la petición no está autenticada. |
| **`sessionId`** | Sesión del navegador: se crea al iniciar sesión; `null` en las vistas públicas (antes del login). |
| **`requestId`** | Id de la llamada a la API que confirma o rechaza el hecho (`X-Request-Id`, creado por `lib/api-client.ts`). |
| **Datos sensibles** | `userId` es `null` (la petición no está autenticada); la cuenta nueva va como `new_user_id` (seudónimo). No se guarda el email. |
| **Entrega** | **stream** (segundos). Con el registro abierto, una cuenta creada por alguien ajeno ya puede leer el inventario: hay que poder revisarla y desactivarla en minutos. |
| **Throttle / debounce** | No necesita: su frecuencia es la de una acción humana o de negocio. |
| **Almacenamiento** | `level`: `info`; `value`: NULL; `message`: `Usuario registrado ({user_role})` |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `new_user_id` | string (UUID) | sí | UUID de la cuenta creada. **[seudónimo]** |
| `user_role` | enum: `admin`, `manager`, `user` | sí | Rol asignado (siempre `user` en el autorregistro). |

#### `user_access_changed`

Cambia el acceso de una cuenta.

| | |
|---|---|
| **Clasificación** | Oportunidad identificada |
| **Versión** | `1.0.0` |
| **Emisor** | API (`source: api`) |
| **Se emite** | Tras `PUT /api/v1/users/{id}` que cambia `role` o `is_active`, o tras `DELETE /api/v1/users/{id}`. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador (cabecera `X-Session-Id`); `null` si la petición no viene del backoffice. |
| **`requestId`** | Id de la petición (`X-Request-Id`). |
| **Datos sensibles** | `target_user_id` es seudónimo (UUID). No se guardan emails. |
| **Entrega** | **stream** (segundos). Una concesión de administrador fuera de proceso es una escalada de privilegios: se revisa en el momento. |
| **Throttle / debounce** | No necesita: su frecuencia es la de una acción humana o de negocio. |
| **Almacenamiento** | `level`: `info`; `value`: NULL; `message`: `Acceso de un usuario cambiado: {change} ({previous_role} → {new_role})` |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `target_user_id` | string (UUID) | sí | UUID de la cuenta afectada. **[seudónimo]** |
| `change` | enum: `role_changed`, `activated`, `deactivated`, `deleted` | sí | Qué cambió. |
| `previous_role` | enum: `admin`, `manager`, `user` | no | Rol anterior (en `role_changed`). |
| `new_role` | enum: `admin`, `manager`, `user` | no | Rol nuevo (en `role_changed`). |
| `actor_role` | enum: `admin`, `manager`, `user` | sí | Rol de quien hace el cambio. |
| `self_change` | boolean | sí | `true` si la cuenta afectada es la del propio actor. |

#### `password_reset_requested`

Se solicita un enlace de recuperación de contraseña.

| | |
|---|---|
| **Clasificación** | Oportunidad identificada |
| **Versión** | `1.0.0` |
| **Emisor** | API (`source: api`) |
| **Se emite** | Al recibir `POST /api/v1/auth/forgot-password`, exista o no la cuenta (la respuesta al usuario es neutra). |
| **`userId`** | `null`: la petición no está autenticada. |
| **`sessionId`** | Sesión del navegador (cabecera `X-Session-Id`); `null` si la petición no viene del backoffice. |
| **`requestId`** | Id de la petición (`X-Request-Id`). |
| **Datos sensibles** | **Sí (sanitizado).** El email va como `account_fingerprint`; la IP, truncada. `account_found` solo se usa internamente y nunca llega al usuario. |
| **Entrega** | **stream** (segundos). Una ráfaga contra cuentas inexistentes (enumeración) solo se frena si se detecta mientras ocurre. |
| **Throttle / debounce** | No necesita: su frecuencia es la de una acción humana o de negocio. |
| **Almacenamiento** | `level`: `info`; `value`: NULL; `message`: `Restablecimiento de contraseña solicitado (cuenta encontrada: {account_found})` |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `account_fingerprint` | string | sí | HMAC-SHA256 del email normalizado (minúsculas, sin espacios) con la clave `TELEMETRY_HASH_KEY`, truncado a 16 caracteres hexadecimales. Permite agrupar intentos por cuenta sin guardar el email. **[sanitizado]** |
| `account_found` | boolean | sí | `true` si el email tiene cuenta activa. |
| `client_network` | string (máx. 43) | sí | IP de origen truncada: /24 en IPv4 (`203.0.113.0/24`) o /48 en IPv6. Nunca la IP completa. **[sanitizado]** |

#### `password_reset_completed`

Una contraseña se restablece con un enlace de recuperación.

| | |
|---|---|
| **Clasificación** | Oportunidad identificada |
| **Versión** | `1.0.0` |
| **Emisor** | Navegador (`source: browser`) |
| **Se emite** | En `/reset-password`, al recibir el 200 de `POST /api/v1/auth/reset-password`. `link_age_minutes` sale del `iat` del token del enlace, leído sin verificar la firma. |
| **`userId`** | `null`: la petición no está autenticada. |
| **`sessionId`** | Sesión del navegador: se crea al iniciar sesión; `null` en las vistas públicas (antes del login). |
| **`requestId`** | Id de la llamada a la API que confirma o rechaza el hecho (`X-Request-Id`, creado por `lib/api-client.ts`). |
| **Datos sensibles** | `userId` es `null`: la vista es pública y el `sub` del enlace no se lee. No se emiten el enlace ni el token. |
| **Entrega** | **batch** (diario (cierre 02:00 hora local)). Simplificar el flujo de recuperación se decide con la tasa semanal. |
| **Throttle / debounce** | No necesita: su frecuencia es la de una acción humana o de negocio. |
| **Almacenamiento** | `level`: `info`; `value`: `link_age_minutes`; `message`: `Contraseña restablecida con un enlace de {link_age_minutes} min` |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `link_age_minutes` | integer (≥ 0) | sí | Minutos desde que se emitió el enlace. |

#### `password_reset_link_rejected`

Un enlace de recuperación se rechaza.

| | |
|---|---|
| **Clasificación** | Oportunidad identificada |
| **Versión** | `1.0.0` |
| **Emisor** | Navegador (`source: browser`) |
| **Se emite** | En `/reset-password`, al recibir `invalid_reset_token`, `reset_token_expired` o `reset_token_used` de `POST /api/v1/auth/reset-password/validate` (al abrir el enlace) o de `/reset-password` (al enviar la contraseña). |
| **`userId`** | `null`: la petición no está autenticada. |
| **`sessionId`** | Sesión del navegador: se crea al iniciar sesión; `null` en las vistas públicas (antes del login). |
| **`requestId`** | Id de la llamada a la API que confirma o rechaza el hecho (`X-Request-Id`, creado por `lib/api-client.ts`). |
| **Datos sensibles** | Ninguno. No se guarda el token ni el email. |
| **Entrega** | **batch** (diario (cierre 02:00 hora local)). Ajustar la caducidad del enlace o el texto del correo es una decisión de configuración. |
| **Throttle / debounce** | No necesita: su frecuencia es la de una acción humana o de negocio. |
| **Almacenamiento** | `level`: `warn`; `value`: NULL; `message`: `Enlace de restablecimiento rechazado en {stage} ({rejection_reason})` |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `rejection_reason` | enum: `invalid_reset_token`, `reset_token_expired`, `reset_token_used` | sí | Motivo del rechazo. |
| `stage` | enum: `validate`, `reset` | sí | `validate` (al abrir el enlace) o `reset` (al enviar la contraseña). |

#### `password_changed`

Un usuario cambia su propia contraseña.

| | |
|---|---|
| **Clasificación** | Oportunidad identificada |
| **Versión** | `1.0.0` |
| **Emisor** | Navegador (`source: browser`) |
| **Se emite** | En `/account/change-password`, al recibir el 200 de `POST /api/v1/auth/change-password` (`channel: change_password`). El canal `user_update` queda para el emisor de la API: el backoffice no cambia contraseñas con `PUT /users/{id}`. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador: se crea al iniciar sesión; `null` en las vistas públicas (antes del login). |
| **`requestId`** | Id de la llamada a la API que confirma o rechaza el hecho (`X-Request-Id`, creado por `lib/api-client.ts`). |
| **Datos sensibles** | Ninguno. |
| **Entrega** | **batch** (diario (cierre 02:00 hora local)). Exigir o no la renovación periódica es una política, no una reacción. |
| **Throttle / debounce** | No necesita: su frecuencia es la de una acción humana o de negocio. |
| **Almacenamiento** | `level`: `info`; `value`: `days_since_last_change`; `message`: `Contraseña cambiada ({channel})` |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `days_since_last_change` | integer (≥ 0) | no | Días desde el cambio anterior (`password_changed_at`); ausente si nunca cambió. |
| `channel` | enum: `change_password`, `user_update` | sí | Ruta usada. |

### Navegación y abandono

#### `page_viewed`

El backoffice muestra una vista.

| | |
|---|---|
| **Clasificación** | Oportunidad identificada |
| **Versión** | `1.0.0` |
| **Emisor** | Navegador (`source: browser`) |
| **Se emite** | Al mostrar una ruta del backoffice, en la carga inicial y en cada navegación sin recarga. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador: se crea al iniciar sesión; `null` en las vistas públicas (antes del login). |
| **`requestId`** | `null`: no está ligado a una petición a la API. |
| **Datos sensibles** | Ninguno. La ruta va como plantilla (`/talento/candidates/[id]`), sin ids reales ni query string. `userId` es `null` en las vistas públicas. |
| **Entrega** | **batch** (diario (cierre 02:00 hora local)). Reordenar el menú o retirar secciones se decide con semanas de uso. |
| **Throttle / debounce** | Se ignora una segunda vista de la misma ruta en menos de 1 s (doble montaje de React en desarrollo, recargas dobles). |
| **Almacenamiento** | `level`: `info`; `value`: NULL; `message`: `Vista de {route}` |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `route` | string | sí | Plantilla de la ruta, nunca la URL real: `/api/v1/inventory/products/{ingredient_id}` en la API, `/talento/candidates/[id]` en el backoffice. Sin query string. |
| `previous_route` | string | no | Ruta anterior (plantilla); ausente en la carga inicial. |
| `navigation_type` | enum: `initial`, `client` | sí | `initial` (carga completa) o `client` (sin recarga). |
| `user_role` | enum: `admin`, `manager`, `user` | no | Rol del usuario en las vistas protegidas. |

#### `form_validation_failed`

Un formulario bloquea el envío por errores de validación.

| | |
|---|---|
| **Clasificación** | Oportunidad identificada |
| **Versión** | `1.0.0` |
| **Emisor** | Navegador (`source: browser`) |
| **Se emite** | Al pulsar enviar con campos inválidos según la validación del navegador. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador: se crea al iniciar sesión; `null` en las vistas públicas (antes del login). |
| **`requestId`** | `null`: no está ligado a una petición a la API. |
| **Datos sensibles** | Ninguno. Solo nombres de campo, nunca los valores escritos. |
| **Entrega** | **batch** (diario (cierre 02:00 hora local)). Rediseñar campos se decide con el acumulado. |
| **Throttle / debounce** | Uno por formulario cada 2 s (doble clic en enviar). |
| **Almacenamiento** | `level`: `warn`; `value`: `error_count`; `message`: `Formulario {form_id} bloqueado por {error_count} campos inválidos` |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `form_id` | enum: `login`, `register`, `forgot_password`, `reset_password`, `change_password`, `profile`, `inbound_order`, `outbound_order`, `supplier`, `supplier_rate`, `incident`, `incident_upload`, `candidate`, `candidate_note` | sí | Formulario del backoffice. |
| `invalid_fields` | array de string | sí | Campos con error. |
| `error_count` | integer (≥ 1) | sí | Número de campos con error. |

#### `form_abandoned`

Un formulario empezado se abandona sin enviar.

| | |
|---|---|
| **Clasificación** | Oportunidad identificada |
| **Versión** | `1.0.0` |
| **Emisor** | Navegador (`source: browser`) |
| **Se emite** | Al salir de la vista, cerrar el modal o cerrar la pestaña con al menos un campo modificado y sin envío correcto. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador: se crea al iniciar sesión; `null` en las vistas públicas (antes del login). |
| **`requestId`** | `null`: no está ligado a una petición a la API. |
| **Datos sensibles** | Ninguno. Solo nombres de campo. |
| **Entrega** | **batch** (diario (cierre 02:00 hora local)). Simplificar formularios se decide con el acumulado. |
| **Throttle / debounce** | Uno por formulario abierto: se emite una sola vez, al salir. |
| **Almacenamiento** | `level`: `info`; `value`: `time_in_form_seconds`; `message`: `Formulario {form_id} abandonado tras {time_in_form_seconds} s ({exit})` |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `form_id` | enum: `login`, `register`, `forgot_password`, `reset_password`, `change_password`, `profile`, `inbound_order`, `outbound_order`, `supplier`, `supplier_rate`, `incident`, `incident_upload`, `candidate`, `candidate_note` | sí | Formulario del backoffice. |
| `last_field` | string | sí | Último campo modificado. |
| `filled_field_count` | integer (≥ 1) | sí | Campos modificados. |
| `time_in_form_seconds` | integer (≥ 0) | sí | Segundos desde el primer cambio. |
| `exit` | enum: `navigation`, `modal_closed`, `tab_closed` | sí | Cómo se salió. |

#### `list_filter_applied`

Se cambia un filtro de una lista.

| | |
|---|---|
| **Clasificación** | Oportunidad identificada |
| **Versión** | `1.0.0` |
| **Emisor** | Navegador (`source: browser`) |
| **Se emite** | Al aplicarse un filtro (en el texto, cuando deja de escribirse durante 500 ms). |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador: se crea al iniciar sesión; `null` en las vistas públicas (antes del login). |
| **`requestId`** | `null`: no está ligado a una petición a la API. |
| **Datos sensibles** | Ninguno. El texto de búsqueda no se emite: solo su longitud. |
| **Entrega** | **batch** (diario (cierre 02:00 hora local)). Mover filtros a la API se decide con el uso de semanas. |
| **Throttle / debounce** | Debounce de 500 ms en los filtros de texto: solo se emite cuando se deja de escribir. |
| **Almacenamiento** | `level`: `info`; `value`: `result_count`; `message`: `Filtro {filter_name} en {list_id}: {result_count} resultados` |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `list_id` | enum: `order_history`, `incident_manager`, `supplier_directory` | sí | Lista del backoffice. |
| `filter_name` | enum: `kind`, `ingredient`, `status`, `origin`, `branch`, `country`, `category` | sí | Filtro cambiado. |
| `filter_value` | string | no | Valor elegido en los filtros de lista cerrada (p. ej. `exit`, `open`); ausente en los de texto y al quitar el filtro. |
| `query_length` | integer (≥ 0) | no | Longitud del texto en los filtros de texto. |
| `result_count` | integer (≥ 0) | sí | Filas que quedan con los filtros activos. |

#### `list_page_extended`

Se piden más filas de una lista larga.

| | |
|---|---|
| **Clasificación** | Oportunidad identificada |
| **Versión** | `1.0.0` |
| **Emisor** | Navegador (`source: browser`) |
| **Se emite** | Al pulsar "Mostrar más". |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador: se crea al iniciar sesión; `null` en las vistas públicas (antes del login). |
| **`requestId`** | `null`: no está ligado a una petición a la API. |
| **Datos sensibles** | Ninguno. |
| **Entrega** | **batch** (diario (cierre 02:00 hora local)). Fijar las filas iniciales o añadir paginación se decide con el acumulado. |
| **Throttle / debounce** | No necesita: su frecuencia es la de una acción humana o de negocio. |
| **Almacenamiento** | `level`: `info`; `value`: `visible_rows`; `message`: `Lista {list_id}: {visible_rows} de {total_rows} filas visibles` |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `list_id` | enum: `order_history`, `incident_manager`, `supplier_directory` | sí | Lista del backoffice. |
| `visible_rows` | integer (≥ 1) | sí | Filas visibles tras el clic. |
| `total_rows` | integer (≥ 1) | sí | Filas de la lista con los filtros activos. |
| `filters_active` | boolean | sí | `true` si hay algún filtro aplicado. |

### Rendimiento

#### `api_latency_recorded`

Duración de una petición a la API.

| | |
|---|---|
| **Clasificación** | Oportunidad identificada |
| **Versión** | `1.0.0` |
| **Emisor** | Navegador (`source: browser`) |
| **Se emite** | En `lib/api-client.ts`, al terminar cada llamada a la API a través del intermediario, con el muestreo de la estrategia de entrega. La duración se mide en el navegador (incluye el paso por el BFF); `cache` sale de la cabecera `X-Cache`. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador: se crea al iniciar sesión; `null` en las vistas públicas (antes del login). |
| **`requestId`** | Id de la llamada a la API que confirma o rechaza el hecho (`X-Request-Id`, creado por `lib/api-client.ts`). |
| **Datos sensibles** | Ninguno. La ruta va como plantilla. `userId` es `null` en las rutas públicas. |
| **Entrega** | **batch** (cada hora). Decidir dónde cachear o fijar objetivos de latencia usa percentiles por hora y por día. Las caídas, que sí son urgentes, las detectan `server_error_occurred` y `api_connection_failed` en stream. |
| **Throttle / debounce** | **Muestreo:** se emite siempre si `duration_ms` ≥ 300 o `status_code` ≥ 400; el resto, 1 de cada 10 peticiones, elegidas por el `requestId` (determinista). `sample_rate` indica la tasa aplicada (1 o 0,1) para reconstruir los recuentos. |
| **Almacenamiento** | `level`: `info`; `value`: `duration_ms`; `message`: `{method} {route} → {status_code} en {duration_ms} ms` |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `method` | enum: `GET`, `POST`, `PUT`, `PATCH`, `DELETE` | sí | Método HTTP. |
| `route` | string | sí | Plantilla de la ruta, nunca la URL real: `/api/v1/inventory/products/{ingredient_id}` en la API, `/talento/candidates/[id]` en el backoffice. Sin query string. |
| `status_code` | integer (100–599) | sí | Código HTTP de la respuesta. |
| `duration_ms` | number (≥ 0) | sí | Duración en milisegundos. |
| `cache` | enum: `HIT`, `MISS` | no | Resultado de la caché en las rutas cacheadas (`X-Cache`). |
| `sample_rate` | number (> 0) | sí | Tasa de muestreo aplicada a esta medición: 1 (siempre: lenta o con error) o 0.1 (1 de cada 10). |

#### `page_performance_recorded`

Métricas de carga de una vista.

| | |
|---|---|
| **Clasificación** | Oportunidad identificada |
| **Versión** | `1.0.0` |
| **Emisor** | Navegador (`source: browser`) |
| **Se emite** | Al ocultarse o cerrarse la pestaña, cuando las métricas son definitivas, una vez por carga del backoffice: Web Vitals (useReportWebVitals) solo mide la carga inicial, no las navegaciones sin recarga. `data_ready_ms` todavía no se emite. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador: se crea al iniciar sesión; `null` en las vistas públicas (antes del login). |
| **`requestId`** | `null`: no está ligado a una petición a la API. |
| **Datos sensibles** | Ninguno. No se emite el user agent completo: solo la clase de dispositivo. |
| **Entrega** | **batch** (diario (cierre 02:00 hora local)). Priorizar optimizaciones y fijar presupuestos de rendimiento usa la distribución de días. |
| **Throttle / debounce** | Uno por vista mostrada. |
| **Almacenamiento** | `level`: `info`; `value`: `lcp_ms`; `message`: `Carga de {route}: LCP {lcp_ms} ms, CLS {cls}, INP {inp_ms} ms` |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `route` | string | sí | Plantilla de la ruta, nunca la URL real: `/api/v1/inventory/products/{ingredient_id}` en la API, `/talento/candidates/[id]` en el backoffice. Sin query string. |
| `lcp_ms` | number (≥ 0) | no | Largest Contentful Paint, en ms. |
| `cls` | number (≥ 0) | no | Cumulative Layout Shift. |
| `inp_ms` | number (≥ 0) | no | Interaction to Next Paint, en ms (si hubo interacción). |
| `data_ready_ms` | number (≥ 0) | no | Ms desde la navegación hasta que la vista muestra sus datos (fin de la carga de `useAsyncData`). |
| `device_class` | enum: `mobile`, `tablet`, `desktop` | sí | Clase por ancho de pantalla: `mobile` (< 768 px), `tablet` (768–1023 px) o `desktop`. |
| `effective_connection` | enum: `slow-2g`, `2g`, `3g`, `4g` | no | `navigator.connection.effectiveType`, si el navegador lo ofrece. |

#### `cache_stats_recorded`

Resumen de aciertos y fallos de una caché.

| | |
|---|---|
| **Clasificación** | Oportunidad identificada |
| **Versión** | `1.0.0` |
| **Emisor** | API (`source: api`) |
| **Se emite** | Cada 5 minutos por cada caché del inventario, con los contadores de esa ventana. |
| **`userId`** | `null`: lo emite un proceso, no un usuario. |
| **`sessionId`** | `null`: es un resumen del proceso. |
| **`requestId`** | `null`: agrega muchas peticiones. |
| **Datos sensibles** | Ninguno. |
| **Entrega** | **batch** (cada hora). Ajustar TTL es una decisión de configuración con tendencias de horas. |
| **Throttle / debounce** | Ya es un agregado: uno por caché cada 5 minutos. |
| **Almacenamiento** | `level`: `info`; `value`: NULL; `message`: `Caché {cache_name}: {hits} aciertos y {misses} fallos` |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `cache_name` | enum: `inventory_products`, `inventory_orders` | sí | Caché. |
| `hits` | integer (≥ 0) | sí | Aciertos en la ventana. |
| `misses` | integer (≥ 0) | sí | Fallos en la ventana. |
| `invalidations` | integer (≥ 0) | sí | Invalidaciones en la ventana. |
| `window_seconds` | integer (≥ 1) | sí | Duración de la ventana. |

### Errores

#### `api_error_returned`

La API responde con un error 4xx.

| | |
|---|---|
| **Clasificación** | Oportunidad identificada |
| **Versión** | `1.0.0` |
| **Emisor** | Navegador (`source: browser`) |
| **Se emite** | En `lib/api-client.ts`, al recibir cualquier 4xx con el formato `{"error": {"code", "message"}}`. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador: se crea al iniciar sesión; `null` en las vistas públicas (antes del login). |
| **`requestId`** | Id de la llamada a la API que confirma o rechaza el hecho (`X-Request-Id`, creado por `lib/api-client.ts`). |
| **Datos sensibles** | Ninguno. No se guarda el `message` ni el cuerpo; solo el código. `userId` es `null` si la petición no estaba autenticada. |
| **Entrega** | **batch** (cada hora). Corregir flujos que provocan errores evitables se decide con el acumulado; los errores graves (500) van por su propio evento en stream. |
| **Throttle / debounce** | Un mismo (`route`, `error_code`, `userId`) se emite como máximo una vez cada 10 s: un script que repite la misma petición fallida no multiplica el volumen. |
| **Almacenamiento** | `level`: `warn`; `value`: NULL; `message`: `{method} {route} → {status_code} {error_code}` |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `method` | enum: `GET`, `POST`, `PUT`, `PATCH`, `DELETE` | sí | Método HTTP. |
| `route` | string | sí | Plantilla de la ruta, nunca la URL real: `/api/v1/inventory/products/{ingredient_id}` en la API, `/talento/candidates/[id]` en el backoffice. Sin query string. |
| `status_code` | integer (400–499) | sí | Código 4xx. |
| `error_code` | string | sí | `error.code` de la respuesta (p. ej. `duplicate_sku`, `http_405`). |

#### `server_error_occurred`

Una excepción no controlada produce un 500.

| | |
|---|---|
| **Clasificación** | Oportunidad identificada |
| **Versión** | `1.0.0` |
| **Emisor** | API (`source: api`) |
| **Se emite** | Al responder 500 `internal_error`. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador (cabecera `X-Session-Id`); `null` si la petición no viene del backoffice. |
| **`requestId`** | Id de la petición (`X-Request-Id`). |
| **Datos sensibles** | Ninguno. No se emite el mensaje de la excepción (puede contener datos): solo su tipo y una huella. |
| **Entrega** | **stream** (segundos). Un 500 es un fallo de la API que hay que atender ya: puede estar impidiendo registrar órdenes en todos los locales. |
| **Throttle / debounce** | Una vez por `error_fingerprint` cada 60 s, con el recuento en el log del emisor. |
| **Almacenamiento** | `level`: `error`; `value`: NULL; `message`: `{method} {route} → 500 ({exception_type})` |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `method` | enum: `GET`, `POST`, `PUT`, `PATCH`, `DELETE` | sí | Método HTTP. |
| `route` | string | sí | Plantilla de la ruta, nunca la URL real: `/api/v1/inventory/products/{ingredient_id}` en la API, `/talento/candidates/[id]` en el backoffice. Sin query string. |
| `exception_type` | string | sí | Clase de la excepción (p. ej. `OperationalError`). |
| `error_fingerprint` | string | sí | Huella de 16 caracteres hexadecimales del tipo de error y del primer marco de la pila (archivo y función, sin números de línea), para agrupar el mismo fallo. En el navegador es FNV-1a de 64 bits: crypto.subtle (SHA-256) no existe sin HTTPS. |

#### `frontend_error_captured`

Un error de JavaScript no controlado en el backoffice.

| | |
|---|---|
| **Clasificación** | Oportunidad identificada |
| **Versión** | `1.0.0` |
| **Emisor** | Navegador (`source: browser`) |
| **Se emite** | En `window.onerror`, en `unhandledrejection` y al mostrarse la pantalla de error de una vista (`error.tsx`). |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador: se crea al iniciar sesión; `null` en las vistas públicas (antes del login). |
| **`requestId`** | `null`: no está ligado a una petición a la API. |
| **Datos sensibles** | **Posible (sanitizado).** El mensaje se recorta a 200 caracteres y se le sustituyen emails, números de 4 o más cifras y UUID por `[redacted]` antes de emitirlo. |
| **Entrega** | **batch** (cada hora). La decisión es priorizar correcciones por número de sesiones afectadas, con datos de horas. Un despliegue roto se ve también en `api_error_returned` y en las consultas de soporte. |
| **Throttle / debounce** | Una vez por `error_fingerprint` y sesión cada 60 s, y como máximo 20 por sesión (un error en bucle no inunda la telemetría). |
| **Almacenamiento** | `level`: `error`; `value`: NULL; `message`: `{error_name} en {route}: {message_sanitized}` |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `route` | string | sí | Plantilla de la ruta, nunca la URL real: `/api/v1/inventory/products/{ingredient_id}` en la API, `/talento/candidates/[id]` en el backoffice. Sin query string. |
| `error_name` | string (máx. 60) | sí | Tipo de error (p. ej. `TypeError`). |
| `message_sanitized` | string (máx. 200) | sí | Mensaje recortado y saneado. **[sanitizado]** |
| `error_fingerprint` | string | sí | Huella de 16 caracteres hexadecimales del tipo de error y del primer marco de la pila (archivo y función, sin números de línea), para agrupar el mismo fallo. En el navegador es FNV-1a de 64 bits: crypto.subtle (SHA-256) no existe sin HTTPS. |
| `source` | enum: `window_error`, `unhandled_rejection`, `error_boundary` | sí | Dónde se capturó. |

#### `api_connection_failed`

El backoffice no llega a la API.

| | |
|---|---|
| **Clasificación** | Oportunidad identificada |
| **Versión** | `1.1.0` |
| **Emisor** | Navegador (`source: browser`) |
| **Se emite** | En `lib/api-client.ts`, al recibir del intermediario 502 `api_unavailable`, 504 `api_timeout` o 500 `api_not_configured`. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador: se crea al iniciar sesión; `null` en las vistas públicas (antes del login). |
| **`requestId`** | Id de la llamada a la API que confirma o rechaza el hecho (`X-Request-Id`, creado por `lib/api-client.ts`). |
| **Datos sensibles** | Ninguno. `userId` es el de la sesión del navegador. |
| **Entrega** | **stream** (segundos). Sin API, ningún local puede registrar órdenes: es un incidente de disponibilidad que se abre en minutos. |
| **Throttle / debounce** | Una vez por sesión cada 30 s mientras la API no responde. |
| **Almacenamiento** | `level`: `error`; `value`: `duration_ms`; `message`: `{method} {route} sin respuesta de la API ({failure}, {status_code})` |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `method` | enum: `GET`, `POST`, `PUT`, `PATCH`, `DELETE` | sí | Método HTTP. |
| `route` | string | sí | Plantilla de la ruta de la API que se intentó. |
| `failure` | enum: `api_unavailable`, `api_timeout`, `api_not_configured` | sí | Motivo. |
| `status_code` | enum: `500`, `502`, `504` | sí | 502, 504 o 500. |
| `duration_ms` | number (≥ 0) | sí | Ms hasta el fallo. |

#### `email_delivery_failed`

Un correo no sale.

| | |
|---|---|
| **Clasificación** | Oportunidad identificada |
| **Versión** | `1.0.0` |
| **Emisor** | Proceso (`source: process`) |
| **Se emite** | En la tarea en segundo plano de envío (`send_safely`) cuando el proveedor falla o el envío está desactivado (falta `RESEND_API_KEY`). |
| **`userId`** | `null`: lo emite un proceso, no un usuario. |
| **`sessionId`** | `null`: corre fuera de la petición. |
| **`requestId`** | Id de la petición que pidió el correo. |
| **Datos sensibles** | Ninguno. Nunca se emiten el destinatario, el asunto ni el enlace. |
| **Entrega** | **stream** (segundos). Hay un usuario esperando su enlace de recuperación ahora mismo; una configuración rota afecta a todos los siguientes. |
| **Throttle / debounce** | No necesita: su frecuencia es la de una acción humana o de negocio. |
| **Almacenamiento** | `level`: `error`; `value`: NULL; `message`: `Correo {email_kind} no enviado ({failure})` |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `email_kind` | enum: `password_reset` | sí | Tipo de correo. |
| `failure` | enum: `provider_error`, `disabled` | sí | `provider_error` (Resend respondió con error) o `disabled` (sin clave). |
| `provider_status` | integer (100–599) | no | Código HTTP del proveedor, si respondió. |

### Otras áreas del negocio

#### `supplier_created`

Se da de alta un proveedor.

| | |
|---|---|
| **Clasificación** | Oportunidad identificada |
| **Versión** | `1.0.0` |
| **Emisor** | Navegador (`source: browser`) |
| **Se emite** | En el directorio de proveedores, al recibir el 201 de `POST /api/v1/suppliers`; los datos salen de la respuesta. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador: se crea al iniciar sesión; `null` en las vistas públicas (antes del login). |
| **`requestId`** | Id de la llamada a la API que confirma o rechaza el hecho (`X-Request-Id`, creado por `lib/api-client.ts`). |
| **Datos sensibles** | Ninguno. No se emiten los datos de contacto del proveedor. |
| **Entrega** | **batch** (diario (cierre 02:00 hora local)). Consolidar categorías de proveedores es una decisión trimestral. |
| **Throttle / debounce** | No necesita: su frecuencia es la de una acción humana o de negocio. |
| **Almacenamiento** | `level`: `info`; `value`: NULL; `message`: `Proveedor {supplier_id} dado de alta en {country} ({status})` |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `supplier_id` | integer (≥ 1) | sí | Id del proveedor en el directorio. |
| `country` | enum: `CO`, `US` | sí | País del proveedor (`Colombia`→`CO`, `USA`→`US`). |
| `categories` | array de enum: `carne`, `verduras_y_hortalizas`, `salsas_y_condimentos`, `bebidas`, `packaging`, `productos_limpieza`, `lacteos`, `carbon_y_combustible` | sí | Categorías del proveedor en el directorio. |
| `currency` | enum: `COP`, `USD` | sí | Moneda del local (`COP` en Colombia, `USD` en Florida). Sin conversión. |
| `status` | enum: `active`, `suspended` | sí | Estado del proveedor. |

#### `supplier_rate_updated`

Cambia la tarifa de un proveedor.

| | |
|---|---|
| **Clasificación** | Oportunidad identificada |
| **Versión** | `1.0.0` |
| **Emisor** | Navegador (`source: browser`) |
| **Se emite** | En el directorio, al recibir el 200 de `PATCH /api/v1/suppliers/{id}/rate`; `previous_rate` es la tarifa mostrada antes del cambio. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador: se crea al iniciar sesión; `null` en las vistas públicas (antes del login). |
| **`requestId`** | Id de la llamada a la API que confirma o rechaza el hecho (`X-Request-Id`, creado por `lib/api-client.ts`). |
| **Datos sensibles** | Ninguno. |
| **Entrega** | **batch** (diario (cierre 02:00 hora local)). Renegociar se planifica con el histórico de cambios; la tarifa ya está registrada. |
| **Throttle / debounce** | No necesita: su frecuencia es la de una acción humana o de negocio. |
| **Almacenamiento** | `level`: `info`; `value`: `change_pct`; `message`: `Tarifa del proveedor {supplier_id}: {previous_rate} → {new_rate} {currency} ({change_pct} %)` |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `supplier_id` | integer (≥ 1) | sí | Id del proveedor en el directorio. |
| `country` | enum: `CO`, `US` | sí | País del proveedor. |
| `currency` | enum: `COP`, `USD` | sí | Moneda del local (`COP` en Colombia, `USD` en Florida). Sin conversión. |
| `previous_rate` | number (> 0) | sí | Tarifa anterior por unidad, en `currency`. |
| `new_rate` | number (> 0) | sí | Tarifa nueva por unidad, en `currency`. |
| `change_pct` | number | sí | (new_rate − previous_rate) / previous_rate × 100. |

#### `supplier_status_changed`

Un proveedor se suspende o se reactiva.

| | |
|---|---|
| **Clasificación** | Oportunidad identificada |
| **Versión** | `1.0.0` |
| **Emisor** | Navegador (`source: browser`) |
| **Se emite** | En el directorio, al recibir el 200 de `PATCH /api/v1/suppliers/{id}/status` que cambia el estado. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador: se crea al iniciar sesión; `null` en las vistas públicas (antes del login). |
| **`requestId`** | Id de la llamada a la API que confirma o rechaza el hecho (`X-Request-Id`, creado por `lib/api-client.ts`). |
| **Datos sensibles** | Ninguno. |
| **Entrega** | **batch** (diario (cierre 02:00 hora local)). Buscar proveedores alternativos se decide con la cobertura por categoría, revisada a diario. |
| **Throttle / debounce** | No necesita: su frecuencia es la de una acción humana o de negocio. |
| **Almacenamiento** | `level`: `info`; `value`: NULL; `message`: `Proveedor {supplier_id}: {previous_status} → {new_status}` |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `supplier_id` | integer (≥ 1) | sí | Id del proveedor en el directorio. |
| `country` | enum: `CO`, `US` | sí | País del proveedor. |
| `categories` | array de enum: `carne`, `verduras_y_hortalizas`, `salsas_y_condimentos`, `bebidas`, `packaging`, `productos_limpieza`, `lacteos`, `carbon_y_combustible` | sí | Categorías del proveedor en el directorio. |
| `previous_status` | enum: `active`, `suspended` | sí | Estado del proveedor. |
| `new_status` | enum: `active`, `suspended` | sí | Estado del proveedor. |

#### `supplier_deleted`

Se borra un proveedor.

| | |
|---|---|
| **Clasificación** | Oportunidad identificada |
| **Versión** | `1.0.0` |
| **Emisor** | API (`source: api`) |
| **Se emite** | Tras `DELETE /api/v1/suppliers/{id}`. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador (cabecera `X-Session-Id`); `null` si la petición no viene del backoffice. |
| **`requestId`** | Id de la petición (`X-Request-Id`). |
| **Datos sensibles** | Ninguno. |
| **Entrega** | **batch** (diario (cierre 02:00 hora local)). Revisar si el borrado debió ser suspensión es una tarea periódica. |
| **Throttle / debounce** | No necesita: su frecuencia es la de una acción humana o de negocio. |
| **Almacenamiento** | `level`: `info`; `value`: NULL; `message`: `Proveedor {supplier_id} eliminado ({status_at_deletion})` |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `supplier_id` | integer (≥ 1) | sí | Id del proveedor en el directorio. |
| `country` | enum: `CO`, `US` | sí | País del proveedor. |
| `categories` | array de enum: `carne`, `verduras_y_hortalizas`, `salsas_y_condimentos`, `bebidas`, `packaging`, `productos_limpieza`, `lacteos`, `carbon_y_combustible` | sí | Categorías del proveedor en el directorio. |
| `status_at_deletion` | enum: `active`, `suspended` | sí | Estado del proveedor. |

#### `incident_created`

Se registra una incidencia.

| | |
|---|---|
| **Clasificación** | Oportunidad identificada |
| **Versión** | `1.0.0` |
| **Emisor** | Navegador (`source: browser`) |
| **Se emite** | En el formulario de registro de incidencias, al recibir el 201 de `POST /api/v1/incidents`. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador: se crea al iniciar sesión; `null` en las vistas públicas (antes del login). |
| **`requestId`** | Id de la llamada a la API que confirma o rechaza el hecho (`X-Request-Id`, creado por `lib/api-client.ts`). |
| **Datos sensibles** | Ninguno. No se emiten el título ni la descripción (texto libre). |
| **Entrega** | **batch** (diario (cierre 02:00 hora local)). Planificar visitas y mantenimiento usa el acumulado por sede. La atención de cada incidencia ya ocurre en el gestor, no en la telemetría. |
| **Throttle / debounce** | No necesita: su frecuencia es la de una acción humana o de negocio. |
| **Almacenamiento** | `level`: `info`; `value`: NULL; `message`: `Incidencia {incident_id} ({category}) registrada en {branch}` |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `incident_id` | integer (≥ 1) | sí | Id de la incidencia. |
| `category` | enum: `equipment_failure`, `supply_issue`, `customer_complaint`, `staff_issue`, `facility_issue`, `pos_system`, `delivery_issue`, `other` | sí | Categoría de la incidencia. |
| `origin` | enum: `customer`, `branch`, `internal` | sí | Origen del reporte. |
| `branch` | enum: `central`, `medellin_centro`, `medellin_laureles`, `medellin_envigado`, `medellin_bello`, `medellin_itagui`, `bogota_chapinero`, `bogota_usaquen`, `cali_granada`, `barranquilla_norte`, `miami_doral`, `miami_hialeah`, `miami_kendall`, `orlando_international`, `fort_lauderdale` | sí | Sede del gestor de incidencias (`central` si no es un local). |
| `status` | enum: `open`, `in_progress`, `resolved`, `discarded` | sí | Estado de la incidencia. |

#### `incident_status_changed`

Cambia el estado de una incidencia.

| | |
|---|---|
| **Clasificación** | Oportunidad identificada |
| **Versión** | `1.0.0` |
| **Emisor** | Navegador (`source: browser`) |
| **Se emite** | En el gestor de incidencias, al recibir el 200 de `PATCH /api/v1/incidents/{id}/status`; los minutos salen de `created_at` y `updated_at` del listado. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador: se crea al iniciar sesión; `null` en las vistas públicas (antes del login). |
| **`requestId`** | Id de la llamada a la API que confirma o rechaza el hecho (`X-Request-Id`, creado por `lib/api-client.ts`). |
| **Datos sensibles** | Ninguno. |
| **Entrega** | **batch** (diario (cierre 02:00 hora local)). Los tiempos objetivo de respuesta se fijan y revisan con datos de semanas. |
| **Throttle / debounce** | No necesita: su frecuencia es la de una acción humana o de negocio. |
| **Almacenamiento** | `level`: `info`; `value`: `minutes_in_previous_status`; `message`: `Incidencia {incident_id}: {previous_status} → {new_status} tras {minutes_in_previous_status} min` |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `incident_id` | integer (≥ 1) | sí | Id de la incidencia. |
| `category` | enum: `equipment_failure`, `supply_issue`, `customer_complaint`, `staff_issue`, `facility_issue`, `pos_system`, `delivery_issue`, `other` | sí | Categoría de la incidencia. |
| `branch` | enum: `central`, `medellin_centro`, `medellin_laureles`, `medellin_envigado`, `medellin_bello`, `medellin_itagui`, `bogota_chapinero`, `bogota_usaquen`, `cali_granada`, `barranquilla_norte`, `miami_doral`, `miami_hialeah`, `miami_kendall`, `orlando_international`, `fort_lauderdale` | sí | Sede del gestor de incidencias (`central` si no es un local). |
| `previous_status` | enum: `open`, `in_progress`, `resolved`, `discarded` | sí | Estado de la incidencia. |
| `new_status` | enum: `open`, `in_progress`, `resolved`, `discarded` | sí | Estado de la incidencia. |
| `minutes_since_created` | integer (≥ 0) | sí | Minutos desde `created_at`. |
| `minutes_in_previous_status` | integer (≥ 0) | sí | Minutos desde el cambio de estado anterior (`updated_at`). |

#### `incident_transition_rejected`

Se rechaza un cambio de estado no permitido.

| | |
|---|---|
| **Clasificación** | Oportunidad identificada |
| **Versión** | `1.0.0` |
| **Emisor** | Navegador (`source: browser`) |
| **Se emite** | En el gestor, al recibir 400 `invalid_transition` de `PATCH /api/v1/incidents/{id}/status`. La interfaz solo ofrece transiciones válidas: ocurre si otra persona cambió el estado antes. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador: se crea al iniciar sesión; `null` en las vistas públicas (antes del login). |
| **`requestId`** | Id de la llamada a la API que confirma o rechaza el hecho (`X-Request-Id`, creado por `lib/api-client.ts`). |
| **Datos sensibles** | Ninguno. |
| **Entrega** | **batch** (diario (cierre 02:00 hora local)). Revisar el ciclo de vida o la interfaz se decide con el acumulado. |
| **Throttle / debounce** | No necesita: su frecuencia es la de una acción humana o de negocio. |
| **Almacenamiento** | `level`: `warn`; `value`: NULL; `message`: `Incidencia {incident_id}: transición {current_status} → {requested_status} rechazada` |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `incident_id` | integer (≥ 1) | sí | Id de la incidencia. |
| `current_status` | enum: `open`, `in_progress`, `resolved`, `discarded` | sí | Estado de la incidencia. |
| `requested_status` | enum: `open`, `in_progress`, `resolved`, `discarded` | sí | Estado de la incidencia. |

#### `incident_report_analyzed`

Se analiza un CSV de incidentes.

| | |
|---|---|
| **Clasificación** | Oportunidad identificada |
| **Versión** | `1.0.0` |
| **Emisor** | Navegador (`source: browser`) |
| **Se emite** | En `/incidencias`, al recibir el 200 de `POST /api/v1/incidents/analyze`; `file_size_bytes` es el tamaño del archivo elegido. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador: se crea al iniciar sesión; `null` en las vistas públicas (antes del login). |
| **`requestId`** | Id de la llamada a la API que confirma o rechaza el hecho (`X-Request-Id`, creado por `lib/api-client.ts`). |
| **Datos sensibles** | Ninguno. No se emite el contenido del archivo ni su nombre. |
| **Entrega** | **batch** (diario (cierre 02:00 hora local)). La capacitación por calidad de los reportes es periódica. |
| **Throttle / debounce** | No necesita: su frecuencia es la de una acción humana o de negocio. |
| **Almacenamiento** | `level`: `info`; `value`: `invalid_rows`; `message`: `Informe de incidencias analizado: {valid_rows} filas válidas y {invalid_rows} inválidas de {total_rows}` |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `total_rows` | integer (≥ 1) | sí | Filas del CSV. |
| `valid_rows` | integer (≥ 0) | sí | Filas válidas. |
| `invalid_rows` | integer (≥ 0) | sí | Filas inválidas. |
| `invalid_by_rule` | objeto: `missing_location`, `invalid_category`, `empty_description`, `missing_reporter`, `invalid_status`, `closed_without_score`, `score_out_of_range` (enteros ≥ 0) | sí | Filas inválidas por regla del analizador. |
| `file_size_bytes` | integer (1–5242880) | sí | Tamaño del archivo. |

#### `incident_report_exported`

Se descarga el resumen del último análisis.

| | |
|---|---|
| **Clasificación** | Oportunidad identificada |
| **Versión** | `1.0.0` |
| **Emisor** | API (`source: api`) |
| **Se emite** | Tras `GET /api/v1/incidents/results/export`. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador (cabecera `X-Session-Id`); `null` si la petición no viene del backoffice. |
| **`requestId`** | Id de la petición (`X-Request-Id`). |
| **Datos sensibles** | Ninguno. |
| **Entrega** | **batch** (diario (cierre 02:00 hora local)). Mantener o sustituir la exportación se decide con meses de uso. |
| **Throttle / debounce** | No necesita: su frecuencia es la de una acción humana o de negocio. |
| **Almacenamiento** | `level`: `info`; `value`: NULL; `message`: `Informe de incidencias exportado {analysis_age_minutes} min después del análisis` |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `analysis_age_minutes` | integer (≥ 0) | sí | Minutos desde el análisis que se exporta. |

### Procesos internos

#### `api_instance_started`

La API termina de arrancar.

| | |
|---|---|
| **Clasificación** | Oportunidad identificada |
| **Versión** | `1.0.0` |
| **Emisor** | Proceso (`source: process`) |
| **Se emite** | Al final del `lifespan` de `app/main.py`. |
| **`userId`** | `null`: lo emite un proceso, no un usuario. |
| **`sessionId`** | `null`. |
| **`requestId`** | `null`. |
| **Datos sensibles** | Ninguno. No se emite ningún valor de configuración, solo si cada función está activa. |
| **Entrega** | **stream** (segundos). Un reinicio inesperado o un arranque con el correo desactivado en producción hay que verlo en el momento, antes de que lo noten los usuarios. |
| **Throttle / debounce** | No necesita: su frecuencia es la de una acción humana o de negocio. |
| **Almacenamiento** | `level`: `info`; `value`: NULL; `message`: `API iniciada (versión {app_version})` |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `app_version` | string | sí | Versión de la API (`FastAPI.version`). |
| `email_enabled` | boolean | sí | `true` si hay `RESEND_API_KEY`. |
| `suppliers_seeded` | integer (≥ 0) | sí | Proveedores sembrados al arrancar (0 si la tabla ya tenía datos). |

#### `data_seed_executed`

Un script carga o retira datos fuera de la API.

| | |
|---|---|
| **Clasificación** | Oportunidad identificada |
| **Versión** | `1.0.0` |
| **Emisor** | Proceso (`source: process`) |
| **Se emite** | Al terminar `uv run seed`, `uv run seed-inventory`, `scripts/seed_incidents.py` o `scripts/seed_volume.py`. |
| **`userId`** | `null`: lo emite un proceso, no un usuario. |
| **`sessionId`** | `null`. |
| **`requestId`** | `null`. |
| **Datos sensibles** | Ninguno. No se emiten las filas cargadas. |
| **Entrega** | **stream** (segundos). Un script de carga ejecutado contra producción mete datos sin trazabilidad en los indicadores de negocio: hay que detectarlo y retirarlos antes del batch diario. |
| **Throttle / debounce** | No necesita: su frecuencia es la de una acción humana o de negocio. |
| **Almacenamiento** | `level`: `info`; `value`: `affected_rows`; `message`: `Semilla {script} en {target} ({mode}): {affected_rows} filas` |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `script` | enum: `seed_suppliers`, `seed_inventory`, `seed_incidents`, `seed_volume` | sí | Script ejecutado. |
| `mode` | enum: `load`, `clear` | sí | `load` o `clear` (`--clear`). |
| `target` | enum: `tinydb`, `supabase`, `tinydb_and_supabase` | sí | Almacenamiento afectado. |
| `affected_rows` | integer (≥ 0) | sí | Filas insertadas o borradas. |
| `succeeded` | boolean | sí | `false` si terminó con error. |

## 16. Fase de reporte técnico

Los eventos guardados en `telemetry_events` se transforman en un **reporte técnico**: un radar operacional para el equipo de ingeniería sobre el volumen de eventos, los errores, la latencia de la API y los fallos de autenticación, siempre con dimensión temporal (por día UTC). No es un reporte de negocio: nada de ventas, compras ni ingresos, que llegarán con los pipelines de datos.

### 16.1 El pipeline

`services/telemetry/analysis.py` es un paquete local (`brasaland-telemetry`) que la API instala en modo editable con uv, como `packages/shared`. Cada métrica es una función independiente y sin efectos secundarios que recibe la conexión y el período ya resuelto, y sigue siempre el mismo orden:

```
cargar (SQL) → refinar (Pandas) → convertir tipos → agrupar → agregar → servir
```

- **Cargar.** Solo las filas que la métrica necesita: `WHERE timestamp >= :start AND timestamp < :end` (inicio inclusivo, fin exclusivo, en UTC) y, si aplica, `event_type = …` o `event_type IN (…)`. Nunca toda la tabla.
- **Refinar.** Extraer de `tags` las dimensiones que la métrica usa y descartar las filas en las que son nulas.
- **Convertir tipos.** `pd.to_datetime(df["timestamp"], utc=True)` antes de cualquier agrupación temporal, y el día con `.dt.date`.
- **Agrupar y agregar.** `groupby` por día y por la dimensión de la métrica, con `.agg()`, `.count()`, `.sum()` o `.mean()`. Sin bucles.
- **Servir.** Una lista de dicts (`.reset_index().to_dict(orient="records")`), con las fechas en ISO y las tasas como fracción de 0 a 1 con 4 decimales.

### 16.2 Métricas

| Clave | Pregunta operacional | Eventos | Fila |
|---|---|---|---|
| `events_per_day` | ¿Cuánto volumen tiene el sistema cada día y qué parte es aviso o error? | Todos | `{date, total, info, warn, error}` |
| `error_rate_by_type` | ¿Qué tipos de fallo dominan cada día y qué peso tienen sobre el volumen? | Todos (el total del día es el denominador) | `{date, event_type, level, count, rate}`, solo tipos `warn` o `error` |
| `api_latency_by_route` | ¿Qué rutas de la API responden lento y cuánto? | `api_latency_recorded` | `{date, route, samples, avg_ms, max_ms}` |
| `auth_failure_rate` | ¿Qué proporción de los intentos de login falla cada día? | `login_failed` y `login_succeeded` | `{date, attempts, failed, failure_rate}` |

- **Latencia muestreada.** `api_latency_recorded` guarda siempre las peticiones lentas y las de error, y 1 de cada 10 del resto (`sample_rate`). La media se pondera por `1/sample_rate` para que el muestreo no la sesgue hacia las lentas; `samples` es el número de eventos y `max_ms` no se pondera.
- **Nombres.** La consigna llama a los eventos de login `user_login_failed` y `user_login_succeeded`; en este catálogo son `login_failed` y `login_succeeded` (§5).

### 16.3 El endpoint

`GET /telemetry/report?start_date=…&end_date=…`, en el router de telemetría y fuera de `/api/v1`, como el receptor. Exige token y rol `admin` (401 sin token, 403 con otro rol).

- **Período.** Ambos parámetros son opcionales, en ISO 8601 (fecha sola = 00:00 UTC; sin zona = UTC). Sin parámetros, los últimos 7 días hasta ahora; solo `end_date` → 7 días antes; solo `start_date` → hasta ahora. El endpoint resuelve el período **una vez** y lo pasa a cada función, que lo aplica en SQL. 422 si una fecha está mal formada, `invalid_period` si el inicio no es anterior al fin y `period_too_long` por encima de 90 días.
- **Respuesta.** `{"period": {"from", "to"}, "metrics": {"events_per_day", "error_rate_by_type", "api_latency_by_route", "auth_failure_rate"}}`, con `from` y `to` en ISO UTC.
- **Cache.** En memoria, 60 s (`TTLCache`). La clave son los parámetros recibidos, con "now" para el que falte, y el período se resuelve dentro del cálculo: dos peticiones sin parámetros dentro del TTL reciben el mismo resultado sin recalcular. `X-Cache: HIT` o `MISS`. Si la base falla, 503 `telemetry_report_unavailable`, sin guardar nada en cache.

### 16.4 Dashboard

`/telemetria` en el backoffice ("Telemetría técnica", en la sección "Herramientas"). Llega a la API por una ruta propia del intermediario (`app/api/telemetry/report/route.ts`), porque el resto del BFF apunta a `/api/v1`. Muestra el período, dos campos de fecha opcionales, una barra por día apilada por nivel y una tabla por cada otra métrica. Solo visualiza las métricas del reporte. Quien no es admin ve un aviso en lugar de los datos.
