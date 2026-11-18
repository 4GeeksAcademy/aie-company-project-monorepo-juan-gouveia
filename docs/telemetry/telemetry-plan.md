# Plan de Telemetría — Brasaland

Respuesta técnica al RFI del equipo de gestión: qué datos vale la pena capturar hoy en la plataforma de Brasaland (API `services/brasaland-api` y backoffice `uis/backoffice`), y cuáles serán valiosos mañana, **antes de escribir una sola línea de instrumentación**. El plan está pensado para que otro desarrollador lo implemente sin tener que preguntar nada.

- **Entregables:** este documento y [`event-schemas.json`](event-schemas.json) (los esquemas de cada evento).
- **Fuentes:** el briefing de Brasaland (métricas obligatorias, entidades y restricciones), el enunciado del RFI y el código actual del monorepo.
- **Estado:** en redacción, por fases. Esta versión contiene el catálogo (secciones 1 a 6), el envelope, los datos sensibles y las fichas de los 44 eventos (secciones 7 a 9). La estrategia de entrega, los riesgos y exclusiones, y las brechas con el modelo actual llegan en la fase siguiente.

## Índice

1. [Propósito y alcance](#1-propósito-y-alcance)
2. [Método y convenciones](#2-método-y-convenciones)
3. [Métricas obligatorias](#3-métricas-obligatorias)
4. [Flujo de gestión de inventario](#4-flujo-de-gestión-de-inventario)
5. [Catálogo de oportunidades identificadas](#5-catálogo-de-oportunidades-identificadas)
6. [Resumen del catálogo](#6-resumen-del-catálogo)
7. [Event Envelope](#7-event-envelope)
8. [Datos sensibles y PII](#8-datos-sensibles-y-pii)
9. [Fichas de los eventos](#9-fichas-de-los-eventos)

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

## 7. Event Envelope

Todo evento, sea cual sea su emisor, es un objeto JSON con los campos siguientes. **Ningún campo puede faltar:** cuando un dato no aplica, su valor es `null`.

| Campo | Tipo | Valor |
|---|---|---|
| `eventId` | string (UUID v4) | Identificador único del evento, generado por el emisor. El almacenamiento descarta los duplicados por este campo. |
| `timestamp` | string (ISO 8601) | Momento del hecho, en UTC y con milisegundos: `2026-11-18T17:36:46.123Z`. Lo pone el emisor cuando ocurre el hecho, no cuando se envía. |
| `sessionId` | string (UUID v4) o `null` | Sesión del navegador: un UUID que el backoffice crea al abrirse y guarda en `sessionStorage` (uno por pestaña). Viaja en la cabecera `X-Session-Id`. Es `null` en los procesos y en las peticiones que no vienen del backoffice. |
| `userId` | string (UUID) o `null` | La cuenta que actúa: el `sub` del token (`User.id` en TinyDB). Es un identificador seudónimo, nunca el email ni el nombre. Es `null` si no hay usuario autenticado. Cada ficha (sección 9) indica qué valor lleva. |
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
  "source": "api",
  "environment": "production"
}
```

### 7.1 Reglas para quien instrumente

1. **Validar antes de emitir.** El emisor valida cada evento contra `event-schemas.json`. Un evento que no cumple su esquema, por ejemplo porque lleva una clave fuera del allowlist, **no se emite**: se descarta y se cuenta en el log del emisor. Nunca se recorta ni se corrige en silencio.
2. **Las propiedades opcionales se omiten.** Si una propiedad opcional no tiene valor, la clave no se envía. Los `null` son solo para los campos del envelope.
3. **Correlación de extremo a extremo.** Para que `requestId` y `sessionId` lleguen a la API, el navegador añade `X-Request-Id` y `X-Session-Id` a cada llamada (`lib/api-client.ts`). El BFF debe reenviarlas, porque hoy solo copia `Content-Type`, `Accept` y `Authorization`. La API debe leerlas y crear `X-Request-Id` si falta.
4. **Los eventos de negocio de la API se emiten después del `commit`** (sección 2.4). Los rechazos se emiten al construir la respuesta de error.
5. **Las rutas siempre van como plantilla:** `/api/v1/incidents/{incident_id}` o `/talento/candidates/[id]`, nunca con ids reales ni query string.

### 7.2 Cómo está organizado `event-schemas.json`

Es un JSON Schema **draft-07** válido. Un evento es válido si cumple exactamente uno de los 44 esquemas de `oneOf`. El campo `event_type` lo dirige al suyo.

| Ruta | Contenido |
|---|---|
| `definitions/envelope` | Los campos de la tabla anterior, con `additionalProperties: false` |
| `definitions/properties` | Las propiedades que comparten varios eventos (`location_id`, `country`, `product_category`, `route`, `account_fingerprint`…), con su tipo y su dominio |
| `definitions/events/<event_type>` | Un esquema por evento: el envelope (`allOf`), `event_type`, `schemaVersion` y `source` fijos con `const`, y `properties` con sus obligatorias y su allowlist (`additionalProperties: false`). Incluye un ejemplo válido en `examples`. |
| Claves `x-*` de cada evento | Anotaciones documentales que los validadores ignoran: `x-classification` (`obligatorio` u `oportunidad`), `x-category`, `x-emitter`, `x-trigger` y `x-pii` |

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
| **Sanitizado** | Dato personal transformado antes de salir del emisor | `account_fingerprint`: HMAC-SHA256 del email normalizado con la clave `TELEMETRY_HASH_KEY` (distinta de `SECRET_KEY`), truncado a 16 caracteres hexadecimales. `client_network`: IP truncada a /24 (IPv4) o /48 (IPv6). `message_sanitized`: mensaje recortado a 200 caracteres, con emails, números de 4 o más cifras y UUID sustituidos por `[redacted]`. | `login_failed`, `password_reset_requested`, `frontend_error_captured` |

**Por qué HMAC y no un hash simple:** el email tiene pocas variantes probables, así que un SHA-256 sin clave se podría revertir probando emails conocidos. Con una clave secreta del servidor no se puede. Si la clave se rota, las huellas anteriores dejan de agruparse con las nuevas. Es aceptable, porque solo se usan para detectar ráfagas en ventanas cortas.

**Por qué `userId` es `null` en `login_failed` aunque la cuenta exista:** con el `userId` relleno, la telemetría revelaría qué emails tienen cuenta, que es justo lo que la respuesta neutra de la API oculta. La agrupación por cuenta la da `account_fingerprint`.

## 9. Fichas de los eventos

Una ficha por evento, en el mismo orden y con las mismas propiedades que `event-schemas.json`. **El allowlist de cada evento son exactamente las propiedades de su tabla:** cualquier otra clave hace que el evento no se emita. "Obligatoria: sí" significa que la clave debe estar siempre; las opcionales se omiten cuando no hay valor.

### Inventario

#### `inbound_order_created`

Un local registra la llegada de mercancía de un proveedor.

| | |
|---|---|
| **Clasificación** | Obligatorio |
| **Emisor** | API (`source: api`) |
| **Se emite** | Tras el `commit` de `POST /api/v1/inventory/orders/inbound`. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador (cabecera `X-Session-Id`); `null` si la petición no viene del backoffice. |
| **`requestId`** | Id de la petición (`X-Request-Id`). |
| **Datos sensibles** | Ninguno. Describe productos y locales, no personas. |

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
| **Emisor** | API (`source: api`) |
| **Se emite** | Tras el `commit` de `POST /api/v1/inventory/orders/outbound` con motivo de consumo. Una salida de merma emite `stock_waste_registered` en su lugar. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador (cabecera `X-Session-Id`); `null` si la petición no viene del backoffice. |
| **`requestId`** | Id de la petición (`X-Request-Id`). |
| **Datos sensibles** | Ninguno. Describe productos y locales, no personas. |

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
| **Emisor** | API (`source: api`) |
| **Se emite** | Tras el `commit` de `POST /api/v1/inventory/orders/outbound` con motivo de merma. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador (cabecera `X-Session-Id`); `null` si la petición no viene del backoffice. |
| **`requestId`** | Id de la petición (`X-Request-Id`). |
| **Datos sensibles** | Ninguno. Describe productos y locales, no personas. |

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
| **Emisor** | API (`source: api`) |
| **Se emite** | Tras el `commit` de una salida que hace cruzar el mínimo: stock antes ≥ `threshold_quantity` y después < `threshold_quantity`. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador (cabecera `X-Session-Id`); `null` si la petición no viene del backoffice. |
| **`requestId`** | Id de la petición (`X-Request-Id`). |
| **Datos sensibles** | Ninguno. Describe productos y locales, no personas. |

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
| **Emisor** | API (`source: api`) |
| **Se emite** | Al responder 405 a un `PUT`/`PATCH`/`DELETE` sobre una ruta del inventario, o 422 a un `POST` del inventario cuyo cuerpo incluye `current_stock` o `stock`. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador (cabecera `X-Session-Id`); `null` si la petición no viene del backoffice. |
| **`requestId`** | Id de la petición (`X-Request-Id`). |
| **Datos sensibles** | Ninguno. No se guarda el cuerpo de la petición ni el valor de stock que se intentó escribir. |

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
| **Emisor** | API (`source: api`) |
| **Se emite** | Tras el `commit` de una entrada cuyo `unit_cost` se desvía más de `threshold_pct` de la media de los últimos `history_window_days` días del mismo producto y proveedor, con al menos 3 entradas en esa ventana. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador (cabecera `X-Session-Id`); `null` si la petición no viene del backoffice. |
| **`requestId`** | Id de la petición (`X-Request-Id`). |
| **Datos sensibles** | Ninguno. Describe productos y locales, no personas. |

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
| **Emisor** | API (`source: api`) |
| **Se emite** | Al responder 422 `invalid_request` o 404 `ingredient_not_found` a `POST /api/v1/inventory/orders/inbound` u `/outbound`. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador (cabecera `X-Session-Id`); `null` si la petición no viene del backoffice. |
| **`requestId`** | Id de la petición (`X-Request-Id`). |
| **Datos sensibles** | Ninguno. Solo nombres de campo, nunca los valores enviados. |

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
| **Emisor** | API (`source: api`) |
| **Se emite** | Al responder 400 `insufficient_stock` a `POST /api/v1/inventory/orders/outbound` (no se escribe nada). |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador (cabecera `X-Session-Id`); `null` si la petición no viene del backoffice. |
| **`requestId`** | Id de la petición (`X-Request-Id`). |
| **Datos sensibles** | Ninguno. Describe productos y locales, no personas. |

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
| **Emisor** | API (`source: api`) |
| **Se emite** | Tras el `commit` de `POST /api/v1/inventory/products`. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador (cabecera `X-Session-Id`); `null` si la petición no viene del backoffice. |
| **`requestId`** | Id de la petición (`X-Request-Id`). |
| **Datos sensibles** | Ninguno. El nombre de un ingrediente no es un dato personal. |

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
| **Emisor** | API (`source: api`) |
| **Se emite** | Cuando `POST /api/v1/auth/login` emite un token. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador (cabecera `X-Session-Id`); `null` si la petición no viene del backoffice. |
| **`requestId`** | Id de la petición (`X-Request-Id`). |
| **Datos sensibles** | `userId` es un identificador seudónimo (UUID). No se guarda el email. |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `user_role` | enum: `admin`, `manager`, `user` | sí | Rol de la cuenta. |

#### `login_failed`

Un intento de inicio de sesión falla.

| | |
|---|---|
| **Clasificación** | Oportunidad identificada |
| **Emisor** | API (`source: api`) |
| **Se emite** | Cuando `POST /api/v1/auth/login` responde 401 `invalid_credentials` o 403 `inactive_user`. |
| **`userId`** | `null`: la petición no está autenticada. |
| **`sessionId`** | Sesión del navegador (cabecera `X-Session-Id`); `null` si la petición no viene del backoffice. |
| **`requestId`** | Id de la petición (`X-Request-Id`). |
| **Datos sensibles** | **Sí (sanitizado).** El email nunca se emite: va como `account_fingerprint` (HMAC truncado). La IP va truncada (`client_network`). `userId` es `null` aunque la cuenta exista, para no revelar qué emails tienen cuenta. |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `failure_reason` | enum: `invalid_credentials`, `inactive_user` | sí | Motivo del rechazo. |
| `account_fingerprint` | string | sí | HMAC-SHA256 del email normalizado (minúsculas, sin espacios) con la clave `TELEMETRY_HASH_KEY`, truncado a 16 caracteres hexadecimales. Permite agrupar intentos por cuenta sin guardar el email. **[sanitizado]** |
| `client_network` | string (máx. 43) | sí | IP de origen truncada: /24 en IPv4 (`203.0.113.0/24`) o /48 en IPv6. Nunca la IP completa. **[sanitizado]** |

#### `session_expired`

Una petición llega con una sesión caducada.

| | |
|---|---|
| **Clasificación** | Oportunidad identificada |
| **Emisor** | API (`source: api`) |
| **Se emite** | Cuando la dependencia de autenticación responde 401 `token_expired`. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador (cabecera `X-Session-Id`); `null` si la petición no viene del backoffice. |
| **`requestId`** | Id de la petición (`X-Request-Id`). |
| **Datos sensibles** | `userId` sale del `sub` del token caducado (la firma es válida). No se guarda el token. |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `route` | string | sí | Plantilla de la ruta, nunca la URL real: `/api/v1/inventory/products/{ingredient_id}` en la API, `/talento/candidates/[id]` en el backoffice. Sin query string. |
| `token_age_minutes` | integer (≥ 0) | sí | Minutos desde la emisión del token (`iat`). |

#### `auth_token_rejected`

Una petición llega con un token inválido o revocado.

| | |
|---|---|
| **Clasificación** | Oportunidad identificada |
| **Emisor** | API (`source: api`) |
| **Se emite** | Cuando la dependencia de autenticación responde 401 `invalid_token` o `session_revoked`. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador (cabecera `X-Session-Id`); `null` si la petición no viene del backoffice. |
| **`requestId`** | Id de la petición (`X-Request-Id`). |
| **Datos sensibles** | `userId` es el `sub` solo si el token está revocado (firma válida); con `invalid_token` es `null`. No se guarda el token. |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `rejection_reason` | enum: `invalid_token`, `session_revoked` | sí | Motivo del rechazo. |
| `route` | string | sí | Plantilla de la ruta, nunca la URL real: `/api/v1/inventory/products/{ingredient_id}` en la API, `/talento/candidates/[id]` en el backoffice. Sin query string. |

#### `logout_completed`

El usuario cierra sesión.

| | |
|---|---|
| **Clasificación** | Oportunidad identificada |
| **Emisor** | Navegador (`source: browser`) |
| **Se emite** | Al pulsar "Cerrar sesión" en el menú de la cuenta, antes de borrar el token. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador. |
| **`requestId`** | `null`: no hay petición a la API. |
| **Datos sensibles** | Ninguno. |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `route` | string | sí | Vista desde la que se cerró la sesión. |
| `session_duration_seconds` | integer (≥ 0) | sí | Segundos desde el inicio de la sesión del navegador. |

#### `user_registered`

Se crea una cuenta por autorregistro.

| | |
|---|---|
| **Clasificación** | Oportunidad identificada |
| **Emisor** | API (`source: api`) |
| **Se emite** | Tras crear la cuenta con `POST /api/v1/users`. |
| **`userId`** | `null`: la petición no está autenticada. |
| **`sessionId`** | Sesión del navegador (cabecera `X-Session-Id`); `null` si la petición no viene del backoffice. |
| **`requestId`** | Id de la petición (`X-Request-Id`). |
| **Datos sensibles** | `userId` es `null` (la petición no está autenticada); la cuenta nueva va como `new_user_id` (seudónimo). No se guarda el email. |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `new_user_id` | string (UUID) | sí | UUID de la cuenta creada. **[seudónimo]** |
| `user_role` | enum: `admin`, `manager`, `user` | sí | Rol asignado (siempre `user` en el autorregistro). |

#### `user_access_changed`

Cambia el acceso de una cuenta.

| | |
|---|---|
| **Clasificación** | Oportunidad identificada |
| **Emisor** | API (`source: api`) |
| **Se emite** | Tras `PUT /api/v1/users/{id}` que cambia `role` o `is_active`, o tras `DELETE /api/v1/users/{id}`. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador (cabecera `X-Session-Id`); `null` si la petición no viene del backoffice. |
| **`requestId`** | Id de la petición (`X-Request-Id`). |
| **Datos sensibles** | `target_user_id` es seudónimo (UUID). No se guardan emails. |

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
| **Emisor** | API (`source: api`) |
| **Se emite** | Al recibir `POST /api/v1/auth/forgot-password`, exista o no la cuenta (la respuesta al usuario es neutra). |
| **`userId`** | `null`: la petición no está autenticada. |
| **`sessionId`** | Sesión del navegador (cabecera `X-Session-Id`); `null` si la petición no viene del backoffice. |
| **`requestId`** | Id de la petición (`X-Request-Id`). |
| **Datos sensibles** | **Sí (sanitizado).** El email va como `account_fingerprint`; la IP, truncada. `account_found` solo se usa internamente y nunca llega al usuario. |

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
| **Emisor** | API (`source: api`) |
| **Se emite** | Tras el cambio de contraseña de `POST /api/v1/auth/reset-password`. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador (cabecera `X-Session-Id`); `null` si la petición no viene del backoffice. |
| **`requestId`** | Id de la petición (`X-Request-Id`). |
| **Datos sensibles** | `userId` es el dueño del enlace. No se guarda el enlace ni el token. |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `link_age_minutes` | integer (≥ 0) | sí | Minutos desde que se emitió el enlace. |

#### `password_reset_link_rejected`

Un enlace de recuperación se rechaza.

| | |
|---|---|
| **Clasificación** | Oportunidad identificada |
| **Emisor** | API (`source: api`) |
| **Se emite** | Cuando `POST /api/v1/auth/reset-password/validate` o `/reset-password` responde con `invalid_reset_token`, `reset_token_expired` o `reset_token_used`. |
| **`userId`** | `null`: la petición no está autenticada. |
| **`sessionId`** | Sesión del navegador (cabecera `X-Session-Id`); `null` si la petición no viene del backoffice. |
| **`requestId`** | Id de la petición (`X-Request-Id`). |
| **Datos sensibles** | Ninguno. No se guarda el token ni el email. |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `rejection_reason` | enum: `invalid_reset_token`, `reset_token_expired`, `reset_token_used` | sí | Motivo del rechazo. |
| `stage` | enum: `validate`, `reset` | sí | `validate` (al abrir el enlace) o `reset` (al enviar la contraseña). |

#### `password_changed`

Un usuario cambia su propia contraseña.

| | |
|---|---|
| **Clasificación** | Oportunidad identificada |
| **Emisor** | API (`source: api`) |
| **Se emite** | Tras `POST /api/v1/auth/change-password` (también al editar `password` con `PUT /api/v1/users/{id}`). |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador (cabecera `X-Session-Id`); `null` si la petición no viene del backoffice. |
| **`requestId`** | Id de la petición (`X-Request-Id`). |
| **Datos sensibles** | Ninguno. |

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
| **Emisor** | Navegador (`source: browser`) |
| **Se emite** | Al mostrar una ruta del backoffice, en la carga inicial y en cada navegación sin recarga. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador. |
| **`requestId`** | `null`: no está ligado a una petición a la API. |
| **Datos sensibles** | Ninguno. La ruta va como plantilla (`/talento/candidates/[id]`), sin ids reales ni query string. `userId` es `null` en las vistas públicas. |

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
| **Emisor** | Navegador (`source: browser`) |
| **Se emite** | Al pulsar enviar con campos inválidos según la validación del navegador. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador. |
| **`requestId`** | `null`: no está ligado a una petición a la API. |
| **Datos sensibles** | Ninguno. Solo nombres de campo, nunca los valores escritos. |

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
| **Emisor** | Navegador (`source: browser`) |
| **Se emite** | Al salir de la vista, cerrar el modal o cerrar la pestaña con al menos un campo modificado y sin envío correcto. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador. |
| **`requestId`** | `null`: no está ligado a una petición a la API. |
| **Datos sensibles** | Ninguno. Solo nombres de campo. |

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
| **Emisor** | Navegador (`source: browser`) |
| **Se emite** | Al aplicarse un filtro (en el texto, cuando deja de escribirse durante 500 ms). |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador. |
| **`requestId`** | `null`: no está ligado a una petición a la API. |
| **Datos sensibles** | Ninguno. El texto de búsqueda no se emite: solo su longitud. |

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
| **Emisor** | Navegador (`source: browser`) |
| **Se emite** | Al pulsar "Mostrar más". |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador. |
| **`requestId`** | `null`: no está ligado a una petición a la API. |
| **Datos sensibles** | Ninguno. |

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
| **Emisor** | API (`source: api`) |
| **Se emite** | Al terminar cada petición, en el middleware de timing (`app/core/timing.py`), con el muestreo de la estrategia de entrega. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador (cabecera `X-Session-Id`); `null` si la petición no viene del backoffice. |
| **`requestId`** | Id de la petición (`X-Request-Id`). |
| **Datos sensibles** | Ninguno. La ruta va como plantilla. `userId` es `null` en las rutas públicas. |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `method` | enum: `GET`, `POST`, `PUT`, `PATCH`, `DELETE` | sí | Método HTTP. |
| `route` | string | sí | Plantilla de la ruta, nunca la URL real: `/api/v1/inventory/products/{ingredient_id}` en la API, `/talento/candidates/[id]` en el backoffice. Sin query string. |
| `status_code` | integer (100–599) | sí | Código HTTP de la respuesta. |
| `duration_ms` | number (≥ 0) | sí | Duración en milisegundos. |
| `cache` | enum: `HIT`, `MISS` | no | Resultado de la caché en las rutas cacheadas (`X-Cache`). |

#### `page_performance_recorded`

Métricas de carga de una vista.

| | |
|---|---|
| **Clasificación** | Oportunidad identificada |
| **Emisor** | Navegador (`source: browser`) |
| **Se emite** | Al ocultarse la vista o salir de ella (cuando las métricas son definitivas). |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador. |
| **`requestId`** | `null`: no está ligado a una petición a la API. |
| **Datos sensibles** | Ninguno. No se emite el user agent completo: solo la clase de dispositivo. |

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
| **Emisor** | API (`source: api`) |
| **Se emite** | Cada 5 minutos por cada caché del inventario, con los contadores de esa ventana. |
| **`userId`** | `null`: lo emite un proceso, no un usuario. |
| **`sessionId`** | `null`: es un resumen del proceso. |
| **`requestId`** | `null`: agrega muchas peticiones. |
| **Datos sensibles** | Ninguno. |

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
| **Emisor** | API (`source: api`) |
| **Se emite** | Al responder cualquier 4xx con el formato `{"error": {"code", "message"}}`. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador (cabecera `X-Session-Id`); `null` si la petición no viene del backoffice. |
| **`requestId`** | Id de la petición (`X-Request-Id`). |
| **Datos sensibles** | Ninguno. No se guarda el `message` ni el cuerpo; solo el código. `userId` es `null` si la petición no estaba autenticada. |

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
| **Emisor** | API (`source: api`) |
| **Se emite** | Al responder 500 `internal_error`. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador (cabecera `X-Session-Id`); `null` si la petición no viene del backoffice. |
| **`requestId`** | Id de la petición (`X-Request-Id`). |
| **Datos sensibles** | Ninguno. No se emite el mensaje de la excepción (puede contener datos): solo su tipo y una huella. |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `method` | enum: `GET`, `POST`, `PUT`, `PATCH`, `DELETE` | sí | Método HTTP. |
| `route` | string | sí | Plantilla de la ruta, nunca la URL real: `/api/v1/inventory/products/{ingredient_id}` en la API, `/talento/candidates/[id]` en el backoffice. Sin query string. |
| `exception_type` | string | sí | Clase de la excepción (p. ej. `OperationalError`). |
| `error_fingerprint` | string | sí | SHA-256 truncado del tipo de error y del primer marco de la pila (archivo y función, sin números de línea), para agrupar el mismo fallo. |

#### `frontend_error_captured`

Un error de JavaScript no controlado en el backoffice.

| | |
|---|---|
| **Clasificación** | Oportunidad identificada |
| **Emisor** | Navegador (`source: browser`) |
| **Se emite** | En `window.onerror`, en `unhandledrejection` y al mostrarse la pantalla de error de una vista (`error.tsx`). |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador. |
| **`requestId`** | `null`: no está ligado a una petición a la API. |
| **Datos sensibles** | **Posible (sanitizado).** El mensaje se recorta a 200 caracteres y se le sustituyen emails, números de 4 o más cifras y UUID por `[redacted]` antes de emitirlo. |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `route` | string | sí | Plantilla de la ruta, nunca la URL real: `/api/v1/inventory/products/{ingredient_id}` en la API, `/talento/candidates/[id]` en el backoffice. Sin query string. |
| `error_name` | string (máx. 60) | sí | Tipo de error (p. ej. `TypeError`). |
| `message_sanitized` | string (máx. 200) | sí | Mensaje recortado y saneado. **[sanitizado]** |
| `error_fingerprint` | string | sí | SHA-256 truncado del tipo de error y del primer marco de la pila (archivo y función, sin números de línea), para agrupar el mismo fallo. |
| `source` | enum: `window_error`, `unhandled_rejection`, `error_boundary` | sí | Dónde se capturó. |

#### `api_connection_failed`

El backoffice no llega a la API.

| | |
|---|---|
| **Clasificación** | Oportunidad identificada |
| **Emisor** | BFF (`source: bff`) |
| **Se emite** | Cuando el intermediario `app/api/[...path]/route.ts` responde 502 `api_unavailable` o 500 `api_not_configured`. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador (cabecera recibida). |
| **`requestId`** | Id de la petición que no llegó a la API. |
| **Datos sensibles** | Ninguno. `userId` es `null`: el BFF no decodifica el token. |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `method` | enum: `GET`, `POST`, `PUT`, `PATCH`, `DELETE` | sí | Método HTTP. |
| `route` | string | sí | Plantilla de la ruta de la API que se intentó. |
| `failure` | enum: `api_unavailable`, `api_not_configured` | sí | Motivo. |
| `status_code` | enum: `500`, `502` | sí | 502 o 500. |
| `duration_ms` | number (≥ 0) | sí | Ms hasta el fallo. |

#### `email_delivery_failed`

Un correo no sale.

| | |
|---|---|
| **Clasificación** | Oportunidad identificada |
| **Emisor** | Proceso (`source: process`) |
| **Se emite** | En la tarea en segundo plano de envío (`send_safely`) cuando el proveedor falla o el envío está desactivado (falta `RESEND_API_KEY`). |
| **`userId`** | `null`: lo emite un proceso, no un usuario. |
| **`sessionId`** | `null`: corre fuera de la petición. |
| **`requestId`** | Id de la petición que pidió el correo. |
| **Datos sensibles** | Ninguno. Nunca se emiten el destinatario, el asunto ni el enlace. |

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
| **Emisor** | API (`source: api`) |
| **Se emite** | Tras `POST /api/v1/suppliers`. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador (cabecera `X-Session-Id`); `null` si la petición no viene del backoffice. |
| **`requestId`** | Id de la petición (`X-Request-Id`). |
| **Datos sensibles** | Ninguno. No se emiten los datos de contacto del proveedor. |

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
| **Emisor** | API (`source: api`) |
| **Se emite** | Tras `PATCH /api/v1/suppliers/{id}/rate`. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador (cabecera `X-Session-Id`); `null` si la petición no viene del backoffice. |
| **`requestId`** | Id de la petición (`X-Request-Id`). |
| **Datos sensibles** | Ninguno. |

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
| **Emisor** | API (`source: api`) |
| **Se emite** | Tras `PATCH /api/v1/suppliers/{id}/status` que cambia el estado. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador (cabecera `X-Session-Id`); `null` si la petición no viene del backoffice. |
| **`requestId`** | Id de la petición (`X-Request-Id`). |
| **Datos sensibles** | Ninguno. |

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
| **Emisor** | API (`source: api`) |
| **Se emite** | Tras `DELETE /api/v1/suppliers/{id}`. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador (cabecera `X-Session-Id`); `null` si la petición no viene del backoffice. |
| **`requestId`** | Id de la petición (`X-Request-Id`). |
| **Datos sensibles** | Ninguno. |

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
| **Emisor** | API (`source: api`) |
| **Se emite** | Tras `POST /api/v1/incidents`. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador (cabecera `X-Session-Id`); `null` si la petición no viene del backoffice. |
| **`requestId`** | Id de la petición (`X-Request-Id`). |
| **Datos sensibles** | Ninguno. No se emiten el título ni la descripción (texto libre). |

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
| **Emisor** | API (`source: api`) |
| **Se emite** | Tras `PATCH /api/v1/incidents/{id}/status`. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador (cabecera `X-Session-Id`); `null` si la petición no viene del backoffice. |
| **`requestId`** | Id de la petición (`X-Request-Id`). |
| **Datos sensibles** | Ninguno. |

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
| **Emisor** | API (`source: api`) |
| **Se emite** | Cuando `PATCH /api/v1/incidents/{id}/status` responde 400 `invalid_transition`. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador (cabecera `X-Session-Id`); `null` si la petición no viene del backoffice. |
| **`requestId`** | Id de la petición (`X-Request-Id`). |
| **Datos sensibles** | Ninguno. |

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
| **Emisor** | API (`source: api`) |
| **Se emite** | Tras un análisis correcto de `POST /api/v1/incidents/analyze`. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador (cabecera `X-Session-Id`); `null` si la petición no viene del backoffice. |
| **`requestId`** | Id de la petición (`X-Request-Id`). |
| **Datos sensibles** | Ninguno. No se emite el contenido del archivo ni su nombre. |

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
| **Emisor** | API (`source: api`) |
| **Se emite** | Tras `GET /api/v1/incidents/results/export`. |
| **`userId`** | Usuario autenticado (`sub` del token). |
| **`sessionId`** | Sesión del navegador (cabecera `X-Session-Id`); `null` si la petición no viene del backoffice. |
| **`requestId`** | Id de la petición (`X-Request-Id`). |
| **Datos sensibles** | Ninguno. |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `analysis_age_minutes` | integer (≥ 0) | sí | Minutos desde el análisis que se exporta. |

### Procesos internos

#### `api_instance_started`

La API termina de arrancar.

| | |
|---|---|
| **Clasificación** | Oportunidad identificada |
| **Emisor** | Proceso (`source: process`) |
| **Se emite** | Al final del `lifespan` de `app/main.py`. |
| **`userId`** | `null`: lo emite un proceso, no un usuario. |
| **`sessionId`** | `null`. |
| **`requestId`** | `null`. |
| **Datos sensibles** | Ninguno. No se emite ningún valor de configuración, solo si cada función está activa. |

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
| **Emisor** | Proceso (`source: process`) |
| **Se emite** | Al terminar `uv run seed`, `uv run seed-inventory`, `scripts/seed_incidents.py` o `scripts/seed_volume.py`. |
| **`userId`** | `null`: lo emite un proceso, no un usuario. |
| **`sessionId`** | `null`. |
| **`requestId`** | `null`. |
| **Datos sensibles** | Ninguno. No se emiten las filas cargadas. |

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `script` | enum: `seed_suppliers`, `seed_inventory`, `seed_incidents`, `seed_volume` | sí | Script ejecutado. |
| `mode` | enum: `load`, `clear` | sí | `load` o `clear` (`--clear`). |
| `target` | enum: `tinydb`, `supabase`, `tinydb_and_supabase` | sí | Almacenamiento afectado. |
| `affected_rows` | integer (≥ 0) | sí | Filas insertadas o borradas. |
| `succeeded` | boolean | sí | `false` si terminó con error. |
