# Plan de Telemetría — Brasaland

Respuesta técnica al RFI del equipo de gestión: qué datos vale la pena capturar hoy en la plataforma de Brasaland (API `services/brasaland-api` y backoffice `uis/backoffice`), y cuáles serán valiosos mañana, **antes de escribir una sola línea de instrumentación**. El plan está pensado para que otro desarrollador lo implemente sin tener que preguntar nada.

- **Entregables:** este documento y [`event-schemas.json`](event-schemas.json) (los esquemas de cada evento).
- **Fuentes:** el briefing de Brasaland (métricas obligatorias, entidades y restricciones), el enunciado del RFI y el código actual del monorepo.
- **Estado:** en redacción, por fases. Esta versión contiene el catálogo (secciones 1 a 6). El envelope, las fichas por evento, la estrategia de entrega, y los riesgos y exclusiones llegan en las fases siguientes.

## Índice

1. [Propósito y alcance](#1-propósito-y-alcance)
2. [Método y convenciones](#2-método-y-convenciones)
3. [Métricas obligatorias](#3-métricas-obligatorias)
4. [Flujo de gestión de inventario](#4-flujo-de-gestión-de-inventario)
5. [Catálogo de oportunidades identificadas](#5-catálogo-de-oportunidades-identificadas)
6. [Resumen del catálogo](#6-resumen-del-catálogo)

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

Cada evento del catálogo lleva su frase completa y la persona o el equipo que toma esa decisión. Lo que no supera la frase no entra en el catálogo: va a la sección de riesgos y exclusiones, con su motivo.

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

### 2.5 Nombres del briefing frente al modelo actual

Las métricas obligatorias usan las entidades del briefing (`Product`, `InboundOrder`, `OutboundOrder`, `location`, `supplier`). El código del inventario (Hito 5) usa `Ingredient`, `IngredientEntry` e `IngredientExit`. **Los eventos y sus propiedades usan siempre los nombres del briefing**, como `product_id` y `product_category`. La correspondencia con el modelo, y los cambios que necesita el modelo para emitir cada evento, se detallan en la sección de brechas de instrumentación (fase siguiente del plan).

### 2.6 Responsables de las decisiones

| Persona o equipo | Área | Decisiones que alimenta |
|---|---|---|
| Felipe Guerrero | Operaciones de Restaurante | Reabastecimiento, mínimos, mermas, disciplina operativa por local |
| Lucía Fernández | Compras y Proveedores | Consolidación de compras, precios, proveedores |
| Jake Morrison | Formación y Estándares de Calidad | Capacitación del personal, uso correcto del sistema |
| Mariana Restrepo | Dirección Ejecutiva | Alertas estratégicas (precios, pérdidas) |
| Nicolás Park (equipo de Tecnología) | Tecnología | Salud técnica, seguridad, rendimiento, UX del backoffice |

## 3. Métricas obligatorias

Las 6 métricas del briefing son el **piso** del plan. Se instrumentan de punta a punta (captura → almacenamiento) a lo largo de la serie, y están pensadas para agregarse por local, por país y por semana.

| `event_type` | Se dispara cuando… (briefing) | Emisor | Disparo preciso en la plataforma | Responsable |
|---|---|---|---|---|
| `inbound_order_created` | Un local registra la llegada de mercancía de un proveedor | API | Tras el `commit` de `POST /api/v1/inventory/orders/inbound` | Lucía |
| `outbound_order_created` | Un local registra consumo de ingredientes en la preparación de un plato | API | Tras el `commit` de `POST /api/v1/inventory/orders/outbound` con motivo de **consumo** | Felipe |
| `stock_waste_registered` | Un local registra merma (producto vencido, error de cocina, o pérdida/robo) | API | Tras el `commit` de `POST /api/v1/inventory/orders/outbound` con motivo de **merma** | Felipe |
| `stock_threshold_triggered` | El stock de un producto cae por debajo del mínimo configurado para ese local | API | Tras el `commit` de una salida que hace que el stock **cruce** el mínimo: antes ≥ mínimo y después < mínimo | Felipe |
| `direct_stock_edit_rejected` | Un usuario intenta modificar el stock directamente (fuera de una orden) y el sistema lo rechaza | API | Al rechazar un intento de edición directa (definición en §3.2) | Jake |
| `ingredient_price_variance_detected` | El costo unitario de una orden de entrada varía más de un umbral (ej. 10%) respecto al histórico del mismo producto/proveedor | API | Tras el `commit` de una entrada cuyo coste unitario se desvía más del 10 % de la media histórica del mismo producto y proveedor | Lucía y Mariana |

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
- **`stock_threshold_triggered` se emite al cruzar el mínimo, no en cada salida por debajo de él.** Una alerta repetida en cada consumo de un producto ya bajo no aporta nada nuevo y taparía las alertas nuevas. Si el stock se repone por encima del mínimo y vuelve a caer, se emite otra vez.
- **Qué es un "intento de edición directa"** (`direct_stock_edit_rejected`). El sistema no ofrece ninguna forma de editar el stock, así que el intento se reconoce por cómo lo rechaza la API:
  1. `PUT`, `PATCH` o `DELETE` sobre `/api/v1/inventory/products/{id}` o sobre las rutas de órdenes: hoy responde **405** (`http_405`);
  2. un cuerpo de `POST /inventory/products`, `/orders/inbound` u `/orders/outbound` que incluya `current_stock` o `stock`: hoy responde **422** (`invalid_request`, error `extra_forbidden` en ese campo).

  Ambos casos requieren un usuario autenticado. Sin token, la API responde 401 antes de llegar a la ruta, y ese caso lo cubre la autenticación. El backoffice no tiene ningún control para editar el stock, así que estos intentos llegan siempre desde fuera de la interfaz (scripts, Postman, `curl`). Eso es justo lo que quiere detectar el briefing.
- **`ingredient_price_variance_detected` compara con la media histórica del mismo producto y proveedor.** Se usan las entradas de los últimos 90 días, con un mínimo de 3 entradas para considerar que hay histórico, y un umbral del **10 %**, el ejemplo del briefing, configurable. Si no hay histórico suficiente, no se emite: una primera compra no es una anomalía.

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

## 5. Catálogo de oportunidades identificadas

Eventos propuestos por este plan, agrupados por categoría. Para cada uno: emisor, cuándo se dispara, la frase de la regla de oro y el responsable de la decisión. Todos son **oportunidades identificadas**; los obligatorios están en la sección 3.

### 5.1 Inventario

- **`order_validation_failed`** — API — la API rechaza una orden de entrada o de salida por datos inválidos: 422 `invalid_request` o 404 `ingredient_not_found`.
  *"Capturamos `order_validation_failed` porque necesitamos saber qué productos y qué campos acumulan más errores de validación al registrar órdenes, lo que nos permite tomar la decisión de corregir esos datos de catálogo o reforzar la capacitación sobre esos productos."* — Jake.
- **`outbound_order_rejected`** — API — la API rechaza una salida porque supera el stock disponible (400 `insufficient_stock`).
  *"Capturamos `outbound_order_rejected` porque necesitamos saber en qué productos y locales el stock registrado no alcanza para lo que la cocina dice haber consumido, señal de entradas sin registrar o de un stock que no refleja la realidad física, lo que nos permite tomar la decisión de ordenar un conteo físico de ese producto en ese local."* — Felipe.
- **`product_created`** — API — tras el `commit` de `POST /api/v1/inventory/products`.
  *"Capturamos `product_created` porque necesitamos saber cuánto y en qué categorías crece el catálogo de ingredientes de cada país, lo que nos permite tomar la decisión de revisar las altas que duplican productos existentes antes de que fragmenten el histórico de consumo y de precios."* — Lucía.

### 5.2 Autenticación y sesión

- **`login_succeeded`** — API — `POST /auth/login` emite un token.
  *"Capturamos `login_succeeded` porque necesitamos saber cuántos usuarios de cada rol usan el backoffice y en qué franjas horarias, lo que nos permite tomar la decisión de planificar capacitación para los roles que apenas lo usan y concentrar las ventanas de mantenimiento en las horas sin actividad."* — Jake y Nicolás.
- **`login_failed`** — API — `POST /auth/login` responde 401 `invalid_credentials` o 403 `inactive_user`.
  *"Capturamos `login_failed` porque necesitamos saber cuántos intentos fallidos hay por día y si se concentran en una misma cuenta en poco tiempo (posible fuerza bruta) o se reparten (olvido de contraseña), lo que nos permite tomar la decisión de añadir bloqueo temporal por intentos o de promover la recuperación de contraseña."* — Nicolás.
- **`session_expired`** — API — una petición llega con un token caducado (401 `token_expired`).
  *"Capturamos `session_expired` porque necesitamos saber con qué frecuencia la sesión caduca en mitad del trabajo de un operador, lo que nos permite tomar la decisión de ajustar `ACCESS_TOKEN_EXPIRE_MINUTES` o de implementar la renovación del token."* — Nicolás.
- **`auth_token_rejected`** — API — una petición llega con un token inválido (401 `invalid_token`) o revocado tras un cambio de contraseña (401 `session_revoked`).
  *"Capturamos `auth_token_rejected` porque necesitamos saber si llegan tokens manipulados o sesiones ya revocadas que siguen intentando entrar, lo que nos permite tomar la decisión de investigar el origen y, si se repite, rotar `SECRET_KEY`."* — Nicolás.
- **`logout_completed`** — Navegador — el usuario cierra sesión desde el menú de la cuenta.
  *"Capturamos `logout_completed` porque necesitamos saber qué proporción de sesiones se cierran explícitamente y cuántas se dejan abiertas hasta caducar, lo que nos permite tomar la decisión de activar el cierre automático por inactividad en los dispositivos compartidos de los locales."* — Nicolás y Jake.
- **`user_registered`** — API — tras crear una cuenta con `POST /users`, que hoy es un registro abierto.
  *"Capturamos `user_registered` porque necesitamos saber cuántas cuentas se crean por autorregistro y a qué ritmo, lo que nos permite tomar la decisión de cerrar el registro abierto y pasar a altas aprobadas por un administrador."* — Nicolás.
- **`user_access_changed`** — API — un administrador cambia el rol o activa o desactiva una cuenta (`PUT /users/{id}` con `role` o `is_active`), o se elimina una cuenta (`DELETE /users/{id}`: la propia o, si es admin, cualquiera).
  *"Capturamos `user_access_changed` porque necesitamos saber quién concede o retira permisos de administrador y con qué frecuencia, lo que nos permite tomar la decisión de revisar los accesos privilegiados y exigir aprobación doble si se conceden fuera de un proceso."* — Nicolás.
- **`password_reset_requested`** — API — `POST /auth/forgot-password`, exista o no la cuenta.
  *"Capturamos `password_reset_requested` porque necesitamos saber cuántos usuarios olvidan su contraseña y si hay ráfagas de solicitudes contra cuentas que no existen (enumeración), lo que nos permite tomar la decisión de reforzar la formación sobre credenciales o de limitar las solicitudes por origen."* — Nicolás y Jake.
- **`password_reset_completed`** — API — `POST /auth/reset-password` cambia la contraseña.
  *"Capturamos `password_reset_completed` porque necesitamos saber qué proporción de las solicitudes de recuperación terminan en una contraseña nueva, lo que nos permite tomar la decisión de simplificar el flujo de recuperación si la mayoría se queda a medias."* — Nicolás.
- **`password_reset_link_rejected`** — API — un enlace de recuperación se rechaza por inválido, caducado o ya usado (`invalid_reset_token`, `reset_token_expired`, `reset_token_used`).
  *"Capturamos `password_reset_link_rejected` porque necesitamos saber cuántos enlaces caducan antes de usarse o se reutilizan, lo que nos permite tomar la decisión de ajustar `PASSWORD_RESET_EXPIRE_MINUTES` o el texto del correo."* — Nicolás.
- **`password_changed`** — API — el propio usuario cambia su contraseña con `POST /auth/change-password`.
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

- **`api_latency_recorded`** — API — una medición de duración por petición. Es el middleware de timing que ya existe (`app/core/timing.py`), convertido en evento.
  *"Capturamos `api_latency_recorded` porque necesitamos saber qué endpoints son lentos con el volumen real y con qué frecuencia se llaman, lo que nos permite tomar la decisión de dónde cachear, paginar u optimizar consultas, y de fijar objetivos de latencia por endpoint."* — Nicolás.
- **`page_performance_recorded`** — Navegador — las métricas de carga de una vista (LCP, CLS, INP y tiempo hasta mostrar los datos).
  *"Capturamos `page_performance_recorded` porque necesitamos saber cómo de rápido carga el backoffice en los dispositivos y redes reales de los locales, no solo en las mediciones de laboratorio, lo que nos permite tomar la decisión de priorizar optimizaciones por vista y fijar un presupuesto de rendimiento."* — Nicolás.
- **`cache_stats_recorded`** — API — resumen periódico de aciertos y fallos de cada caché del inventario.
  *"Capturamos `cache_stats_recorded` porque necesitamos saber qué proporción de lecturas del inventario sale de la caché con los TTL actuales, lo que nos permite tomar la decisión de ajustar los TTL o retirar una caché que no acierta."* — Nicolás.

### 5.5 Errores

- **`api_error_returned`** — API — cualquier respuesta 4xx de la API, con su código de error.
  *"Capturamos `api_error_returned` porque necesitamos saber qué códigos de error devuelve cada endpoint y con qué frecuencia, lo que nos permite tomar la decisión de corregir los flujos de la interfaz que provocan errores evitables y detectar integraciones mal construidas."* — Nicolás.
- **`server_error_occurred`** — API — una respuesta 500 (`internal_error`) por una excepción no controlada.
  *"Capturamos `server_error_occurred` porque necesitamos saber en qué endpoint y con qué tipo de excepción falla la API, lo que nos permite tomar la decisión de atender el fallo de inmediato y priorizar su corrección frente a otro trabajo."* — Nicolás.
- **`frontend_error_captured`** — Navegador — un error de JavaScript no controlado o una vista que muestra su pantalla de error (`error.tsx`).
  *"Capturamos `frontend_error_captured` porque necesitamos saber qué errores sufren los operadores sin que nadie los reporte, lo que nos permite tomar la decisión de priorizar la corrección de los que afectan a más sesiones."* — Nicolás.
- **`api_connection_failed`** — BFF — el intermediario no consigue respuesta de la API (502 `api_unavailable`) o no está configurado (500 `api_not_configured`).
  *"Capturamos `api_connection_failed` porque necesitamos saber cuándo y durante cuánto tiempo el backoffice se queda sin API, lo que nos permite tomar la decisión de abrir un incidente de disponibilidad y revisar el despliegue."* — Nicolás.
- **`email_delivery_failed`** — Proceso (tarea en segundo plano de la API) — el envío de un correo falla, o no se envía porque falta `RESEND_API_KEY`.
  *"Capturamos `email_delivery_failed` porque necesitamos saber cuántos correos de recuperación no llegan a salir, lo que nos permite tomar la decisión de verificar el dominio de envío en Resend o de corregir la configuración del entorno."* — Nicolás.

### 5.6 Otras áreas del negocio

**Directorio de proveedores**

- **`supplier_created`** — API — tras dar de alta un proveedor (`POST /suppliers`).
  *"Capturamos `supplier_created` porque necesitamos saber cuántos proveedores nuevos entran por país y categoría, lo que nos permite tomar la decisión de consolidar categorías con demasiados proveedores para negociar volumen."* — Lucía.
- **`supplier_rate_updated`** — API — tras cambiar la tarifa de un proveedor (`PATCH /suppliers/{id}/rate`).
  *"Capturamos `supplier_rate_updated` porque necesitamos saber qué proveedores cambian su tarifa, con qué frecuencia y en qué porcentaje, lo que nos permite tomar la decisión de renegociar antes de que el cambio llegue a la factura."* — Lucía.
- **`supplier_status_changed`** — API — tras suspender o reactivar un proveedor (`PATCH /suppliers/{id}/status`).
  *"Capturamos `supplier_status_changed` porque necesitamos saber cuántos proveedores se suspenden y en qué categorías y países, lo que nos permite tomar la decisión de buscar proveedores alternativos donde una suspensión deja una categoría sin cobertura."* — Lucía.
- **`supplier_deleted`** — API — tras borrar un proveedor (`DELETE /suppliers/{id}`).
  *"Capturamos `supplier_deleted` porque necesitamos saber cuándo se borra un proveedor que podría tener entregas en el histórico, lo que nos permite tomar la decisión de sustituir el borrado por la suspensión si se pierde trazabilidad."* — Lucía.

**Gestor de incidencias**

- **`incident_created`** — API — tras registrar una incidencia (`POST /incidents`).
  *"Capturamos `incident_created` porque necesitamos saber qué categorías de incidencia se concentran en qué sedes y con qué origen, lo que nos permite tomar la decisión de dónde enfocar las visitas de supervisión y el mantenimiento preventivo."* — Felipe.
- **`incident_status_changed`** — API — tras cambiar el estado de una incidencia (`PATCH /incidents/{id}/status`).
  *"Capturamos `incident_status_changed` porque necesitamos saber cuánto tarda cada sede en pasar una incidencia de `open` a `in_progress` y a `resolved`, lo que nos permite tomar la decisión de fijar tiempos objetivo de respuesta y apoyar a las sedes que no los cumplen."* — Felipe.
- **`incident_transition_rejected`** — API — la API rechaza un cambio de estado no permitido (400 `invalid_transition`).
  *"Capturamos `incident_transition_rejected` porque necesitamos saber si los usuarios intentan transiciones que el ciclo de vida no permite (por ejemplo, reabrir una incidencia resuelta), lo que nos permite tomar la decisión de revisar el ciclo de vida o explicarlo mejor en la interfaz."* — Felipe y Jake.

**Analizador del CSV de incidentes**

- **`incident_report_analyzed`** — API — tras analizar un CSV con `POST /incidents/analyze`.
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

Por emisor: 32 de la API, 8 del navegador, 1 del BFF y 3 de procesos (la tarea de correo, el arranque de la API y los scripts de carga). Las preguntas del RFI quedan cubiertas así:

| Pregunta | Evento(s) |
|---|---|
| ¿Cuántas órdenes de salida se registran por día? | `outbound_order_created` + `stock_waste_registered` |
| ¿Qué productos acumulan más errores de validación? | `order_validation_failed` (y `form_validation_failed`, antes de enviar) |
| ¿Hay usuarios intentando modificar el stock directamente? | `direct_stock_edit_rejected` |
| ¿Cuándo se disparan más las alertas de stock mínimo? | `stock_threshold_triggered` |
| ¿Cuántos intentos de login fallidos hay por día? | `login_failed` |
| ¿Qué secciones visitan más los operadores? | `page_viewed` |
| ¿Hay flujos que se abandonan a la mitad? | `form_abandoned` |
