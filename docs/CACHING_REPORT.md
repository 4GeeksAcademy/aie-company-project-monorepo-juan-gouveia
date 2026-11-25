# Informe de caching — Brasaland

Análisis y optimización de caching de `services/brasaland-api` (FastAPI) y `uis/backoffice` (Next.js) antes del próximo sprint de funcionalidades. La regla de trabajo fue **medir primero y cachear solo donde coste × frecuencia × estabilidad lo justifican**. Cada decisión de este informe sale de una medición, y cada medición dice cómo repetirla.

- **Rama:** `feature/caching-optimisation` (desde `feature/serialization-audit`).
- **Fecha:** 2026-11-18.
- **Resumen:**
  - **Backend:** se cachean 2 endpoints: `GET /inventory/orders` (5 min) y `GET /inventory/products` (60 s). Un acierto tarda 1,4 ms, frente a 1 287 y 102 ms. Las tres escrituras del inventario limpian la caché.
  - **Frontend:** carga diferida de 2 modales con `next/dynamic`, y las 2 listas largas se pintan de 50 en 50. El historial pasa de 4,7 s a 0,17 s; cambiar el estado de una incidencia, de 740 ms a 11 ms. Un `useMemo` guarda el filtro del historial (~30 ms en un móvil).
  - **No se cachea**, entre otros: la sesión (`/auth/me`), los perfiles, el stock de un ingrediente concreto ni nada de TinyDB.

## Índice

1. [Cómo se midió](#1-cómo-se-midió)
2. [Inventario de endpoints](#2-inventario-de-endpoints)
3. [Decisiones en el backend](#3-decisiones-en-el-backend)
4. [Decisiones en el frontend](#4-decisiones-en-el-frontend)
5. [Intercambios reconocidos](#5-intercambios-reconocidos)
6. [Qué no se cacheó y por qué](#6-qué-no-se-cacheó-y-por-qué)
7. [Límites y trabajo futuro](#7-límites-y-trabajo-futuro)
8. [Verificación](#8-verificación)

## 1. Cómo se midió

### 1.1 Backend: middleware de timing

`app/core/timing.py` registra una línea por petición en el logger `api.timing`, con el formato del briefing:

```
INFO:     api.timing - GET /api/v1/inventory/orders → 200 | 1287.4ms
```

El procedimiento fue el mismo en cada medición:

- API local con un solo proceso de uvicorn y `--no-access-log`;
- 1 petición de calentamiento y 30 secuenciales por cada endpoint `GET`;
- token firmado en local para el administrador, sin escribir nada.

Del log se calculan la mediana, el p95 y el máximo. Los `POST`, `PUT`, `PATCH` y `DELETE` no se lanzaron en bucle, porque escribirían datos; su coste se estima por el código (sección 2).

### 1.2 Volumen realista

Con los datos de partida, todo respondía en milisegundos y el log no distinguía nada. `scripts/seed_volume.py` carga volumen coherente:

- nombres reales en español e inglés;
- proveedores del directorio según país y categoría;
- entregas semanales, consumos y mermas, sin stock negativo;
- incidencias con categoría, origen, sede y estado según su antigüedad.

Todo lleva la marca `VOL-` y se retira con `--clear`.

| Tabla | Antes | Después |
|---|---|---|
| `ingredients` (Supabase) | 6 | 156 |
| `ingredient_entries` | 4 | 7 823 |
| `ingredient_exits` | 3 | 13 317 |
| `incidents` (TinyDB) | 97 | 10 097 |
| `suppliers` (TinyDB, mismo archivo) | 15 | 15 |
| Tamaño de `brasaland-db.json` | 52 KB | 5,2 MB |

### 1.3 Frontend

- **Peso del JavaScript por ruta:** se midió a partir de los manifiestos de `next build`, en gzip.
- **Coste de render:** Chrome sin cabeza (1350×940, mediana de 3 ejecuciones) contra `next start` y la API local con el volumen sembrado. Se midió el tiempo hasta que aparece el resumen de la vista, los nodos del DOM, las tareas largas (más de 50 ms) y la memoria.
- **Coste de los cálculos:** se midió en el navegador con `performance.now()`, a velocidad normal y con la CPU ralentizada 4 veces (equivalente a un móvil).

## 2. Inventario de endpoints

Evaluación de las 35 operaciones de la API en los tres ejes del briefing:

- **Coste:** la mediana medida con el volumen de la sección 1.2, o una estimación por el código en las escrituras.
- **Frecuencia:** cuántas veces la llama el backoffice. No hay telemetría de producción: se estima por qué vistas la llaman y cuándo.
- **Cambio de los datos:** con qué frecuencia cambian los datos de los que depende la respuesta.

| Endpoint | Coste | Frecuencia | Cambio de los datos | Decisión |
|---|---|---|---|---|
| `GET /inventory/orders` | **1 287 ms** (21 140 órdenes, 5,8 MB) | Media: al abrir el historial y al volver a él | Con cada orden registrada | **Caché 5 min** (§3.1) |
| `GET /inventory/products` | **102 ms** (ida y vuelta a Supabase) | **Alta**: lista de ingredientes y desplegables de entrada y salida | Con cada orden o ingrediente nuevo | **Caché 60 s** (§3.2) |
| `GET /inventory/products/{id}` | 88 ms | Media: cada vez que se elige un ingrediente en una salida | Con cada orden de ese ingrediente | No (§6.3) |
| `POST /inventory/products`, `/orders/inbound`, `/orders/outbound` | ~300–550 ms estimados (3–6 idas y vueltas a Supabase; la salida bloquea, suma, inserta y relee) | Media | — (escriben) | No: invalidan la caché |
| `GET /incidents` | 234 ms | Media: al abrir el gestor y con cada filtro | Con cada incidencia o cambio de estado | No (§6.4) |
| `GET /incidents/summary` | 43 ms | Media: al abrir el gestor y tras cada cambio de estado | Ídem | No (§6.4) |
| `GET /incidents/{id}` | 32 ms | Baja (el backoffice no la usa) | Con cada cambio de estado | No (§6.4) |
| `POST /incidents`, `PATCH /incidents/{id}/status` | ~60–150 ms estimados (TinyDB relee y reescribe los 5,2 MB) | Media | — (escriben) | No |
| `POST /incidents/analyze` | Proporcional al CSV (hasta 5 MB) | Baja: subida manual | Cada subida es distinta | No: entrada única |
| `GET /incidents/results/export` | < 5 ms (en memoria) | Baja | Con cada análisis | No: ya es memoria |
| `GET /suppliers`, `/suppliers/{id}` | 33 ms / 32 ms | Media: directorio y desplegable de proveedor de una entrada | Rara vez (altas, tarifas, estado) | No (§6.4) |
| `POST /suppliers`, `PATCH .../rate`, `.../status`, `DELETE` | ~60–150 ms estimados (mismo archivo TinyDB) | Baja | — (escriben) | No |
| `GET /auth/me` | 0,9 ms | **Máxima**: cada carga de una página protegida | Con la sesión del usuario | No (§6.1) |
| `GET /profiles/me`, `/profiles/{id}` | 1,0 ms | Baja | Al editar el perfil | No (§6.2) |
| `PUT /profiles/me`, `/profiles/{id}` | ~5 ms estimados | Baja | — (escriben) | No |
| `GET /users`, `/users/{id}` | ~1 ms estimado (como `/auth/me`) | Baja (solo admin) | Con altas y cambios de cuenta | No (§6.2) |
| `POST /users`, `PUT /users/{id}`, `DELETE /users/{id}` | ~250 ms estimados (bcrypt al registrar o cambiar la contraseña) | Baja | — (escriben) | No |
| `POST /auth/login`, `/change-password`, `/reset-password` | ~250 ms estimados (bcrypt, a propósito) | Baja | — | No: el coste es una defensa |
| `POST /auth/forgot-password`, `/reset-password/validate` | < 10 ms | Baja | Un solo uso | No |
| `GET /health` | 0,4 ms | La consulta el healthcheck de Docker | Nunca | No: no cuesta nada |

**Conclusión del inventario:** las lecturas tienen dos tipos de coste distintos.

- **En Supabase**, el coste es la red: ~90 ms por consulta, aunque se lea una sola fila. En `/orders` se suma el tamaño de la respuesta.
- **En TinyDB**, el coste es volver a leer el archivo entero en cada consulta. Lo pagan incluso los 15 proveedores, que no crecieron: de 2,4 a 33 ms, porque comparten archivo con las 10 097 incidencias.

Solo el primer tipo se resuelve bien con una caché de respuestas (§6.4).

## 3. Decisiones en el backend

### 3.0 Implementación común

- **`app/core/cache.py` (`TTLCache`):** caché en memoria del proceso, segura entre hilos, porque FastAPI ejecuta estos endpoints síncronos en su pool de hilos.
  - **TTL obligatorio:** un TTL de 0 o menos lanza `ValueError`.
  - **`get_or_load(clave, cargar)`:** carga fuera del bloqueo y devuelve si fue un acierto.
  - **`invalidate()`** vacía la caché y sube un **contador de generación**. Así, una lectura que empezó antes de una escritura no guarda su resultado ya obsoleto. Sin ese contador, ese dato viviría todo el TTL.
- **Qué se guarda:** el JSON ya serializado, no los modelos. En `/orders`, unos 400 ms de los 1 287 eran validación y JSON. Un acierto solo envía bytes.
- **Cabecera `X-Cache: HIT | MISS`** en las dos respuestas, para verificarlo desde DevTools o `curl`.
- **El contrato no cambia:** los endpoints mantienen su `response_model`, y la guarda de serialización (35 operaciones) sigue pasando. Una prueba compara el JSON cacheado con el del servicio.
- **Invalidación:** `invalidate_inventory()` limpia las dos cachés justo después del `commit` de `POST /products`, `/orders/inbound` y `/orders/outbound`. Una salida rechazada (400 `insufficient_stock`) no las toca, porque no cambió nada.
- **Sin datos privados:** las dos respuestas son iguales para cualquier usuario autenticado. Ninguna se filtra por usuario, y la etiqueta "Tú" del historial la pone el navegador. El token se comprueba antes de leer la caché: hay pruebas de que sin token la respuesta es 401 aunque la caché esté llena, y de que otro usuario recibe exactamente los mismos bytes.

### 3.1 `GET /api/v1/inventory/orders` — TTL 5 minutos

| | |
|---|---|
| **Coste** | 1 287 ms de mediana (p95 1 478 ms) con 21 140 órdenes. Unos 800 ms son las dos consultas con `join` y la construcción de los modelos; unos 400 ms, la validación y 5,8 MB de JSON. Con 7 órdenes eran 124 ms: el coste crece con el historial. |
| **Frecuencia estimada** | Media: cada apertura de `/inventario/ordenes` y cada vuelta a la vista. Es la consulta habitual para revisar lo registrado. |
| **Cambio de los datos** | Con cada orden registrada, siempre a través de la API. |
| **TTL** | 300 s. |
| **Invalidación** | Cualquier escritura confirmada del inventario. |
| **Resultado** | Acierto: **1,4 ms** de mediana (p95 2,0 ms). El primer fallo tras una invalidación sigue costando ~1,1 s. |

### 3.2 `GET /api/v1/inventory/products` — TTL 60 segundos

| | |
|---|---|
| **Coste** | 102 ms de mediana (p95 177 ms). La agregación de stock en SQL apenas crece con el volumen (98,6 ms con 6 ingredientes): casi todo es la ida y vuelta a Supabase. |
| **Frecuencia estimada** | Alta: es la lectura más compartida del inventario. La piden la lista de ingredientes y los desplegables de los formularios de entrada y de salida, en cada apertura. |
| **Cambio de los datos** | Con cada orden (cambia el stock) o ingrediente nuevo. |
| **Clave** | Una entrada por filtro de país: `products:all`, `products:CO` y `products:US`. |
| **TTL** | 60 s. |
| **Invalidación** | La misma que `/orders`. |
| **Resultado** | Acierto: **1,4 ms** de mediana (p95 1,8 ms). |

## 4. Decisiones en el frontend

### 4.1 Lo que reveló la medición

| Vista (con volumen) | Resumen visible | Nodos DOM | Tareas largas (máx.) | Memoria JS |
|---|---|---|---|---|
| `/inventario/ordenes` (21 140 órdenes) | **4 678 ms** | **444 036** | 2 197 ms (2 096) | 359 MB |
| `/gestor-incidencias` (10 097) | **2 517 ms** | 168 808 | 1 267 ms (910) | 219 MB |
| `/inventario/ingredientes` (156) | 129 ms | 3 074 | 0 | — |
| `/proveedores` (15) | 101 ms | 371 | 0 | — |

Por ruta, el JavaScript pesa 43–49 KB en gzip, y solo 2–6 KB son propios de cada página: el App Router ya divide el código por ruta. **El problema real del frontend no era el bundle, sino pintar listas de miles de filas.**

### 4.2 Carga diferida de componentes (`next/dynamic`)

| Componente | Dónde | Por qué diferirlo | Resultado medido |
|---|---|---|---|
| `SupplierFormModal` | `/proveedores` (`SupplierDirectory`) | Solo aparece al pulsar "Registrar proveedor". El uso habitual del directorio es consultarlo, y el formulario (campos, categorías, validación) no se ve al cargar. | Sale del chunk de entrada a uno propio de **2,5 KB gzip** (6,6 KB sin comprimir), que se descarga al abrirlo. La validación de `lib/proveedores/validation` sigue en la entrada porque `RateEditor` también la usa al cargar la página. |
| `CandidateFormModal` | `/talento` y `/talento/candidates/[id]` (vía `LazyCandidateFormModal`) | Solo aparece al pulsar "Añadir candidato" o "Editar". La declaración diferida vive en un solo módulo que importan las dos páginas. | Chunk propio de **2,4 KB gzip** que se descarga al abrir el modal. |

**Beneficio honesto:** pequeño en bytes, unos 2,5 KB por vista. Está justificado porque cumple el criterio exacto del lazy loading: código que solo se usa en un flujo concreto, tras una acción del usuario, y que no se ve al cargar. El coste es casi nulo: una línea por componente, y el modal tarda unos milisegundos más la primera vez que se abre. Se comprobó en Chrome que cada chunk solo se descarga al abrir el modal.

### 4.3 Diferir el render de las listas largas ("Mostrar más")

El briefing define el lazy loading como "diferir la carga de componentes **o datos** hasta que realmente se necesiten". Aquí los datos ya están en el navegador: lo que se difiere es **pintarlos**.

`hooks/useShowMore.ts` muestra 50 filas y añade 50 más con el botón "Mostrar más" (`components/ShowMoreButton.tsx`, con "Mostrando X de Y" en `aria-live`). Se aplica al historial de órdenes y al gestor de incidencias.

**Regla de reinicio:** la lista vuelve a 50 filas cuando cambia un filtro, porque es otra lista. **No** vuelve a 50 cuando cambian los datos: un cambio de estado sustituye la lista entera y no debe plegarla ni hacer perder la posición. Hay una prueba de Jest para cada caso.

| Medición | Antes | Después |
|---|---|---|
| `/inventario/ordenes`: resumen visible | 4 678 ms, 444 036 nodos, 359 MB | **172 ms**, 1 161 nodos, 21 MB, sin tareas largas |
| `/gestor-incidencias`: resumen visible | 2 517 ms, 168 808 nodos, 219 MB | **459 ms**, 1 250 nodos, 18 MB (incluye ~234 ms de la API) |
| Gestor: cambiar el estado de una incidencia, hasta el siguiente fotograma | 740 ms (CPU x4: **6 770 ms**) | **11 ms** (CPU x4: 71 ms) |

Se descartó un desplegable de 25/50/100 filas. Junto a "Mostrar más" el número cambia de significado (¿filas por página o por clic?), y es ambiguo al cambiarlo con 200 filas ya visibles. El paso fijo de 50 es más simple y suficiente para un historial que se consulta sobre todo por arriba.

### 4.4 `useMemo`: el filtro del historial de órdenes

`OrdersPanel` añade filtros por tipo e ingrediente (nombre o SKU, sin distinguir tildes), aplicados en el navegador porque `GET /inventory/orders` no admite filtros. El cálculo es `filterOrders(orders, filtros)` (`lib/inventory-orders.ts`): una pasada por todas las órdenes que normaliza el texto y cuenta entradas y salidas.

```tsx
const ingredient = useDeferredValue(filters.ingredient);
const filtered = useMemo(
  () => filterOrders(orders, { kind: filters.kind, ingredient }),
  [orders, filters.kind, ingredient]
);
```

- **Coste medido** (21 140 órdenes, media de 5): **4,9 ms** en escritorio y **31,8 ms** con la CPU ralentizada 4 veces. Eso supera un fotograma de 16 ms.
- **Por qué memoizarlo:** sin `useMemo`, el filtro se repetiría en cada render de `OrdersPanel`, también al pulsar "Mostrar más", que no cambia ni las órdenes ni los filtros.
- **Dependencias:**
  - `orders`: la referencia solo cambia cuando llega una respuesta nueva;
  - `filters.kind`;
  - el texto diferido.

  No se incluye el objeto `filters` entero, para no depender de su identidad.
- **`useDeferredValue`:** el campo de búsqueda responde al momento, y el filtro se recalcula cuando el navegador queda libre.
- **Beneficio estimado** (no medido con el Profiler): ~30 ms ahorrados por clic en "Mostrar más" en un móvil.
- **Qué no se memoizó:** el recuento por tipo que hacía antes `OrdersPanel` (0,26 ms; 3 ms con CPU x4) es trivial. Ahora sale de la misma pasada del filtro.

## 5. Intercambios reconocidos

### 5.1 Stock: 60 segundos de posible desactualización

`GET /inventory/products` muestra el stock en la lista de ingredientes y en los desplegables de los formularios. Un stock desactualizado podría llevar a un encargado a intentar una salida que ya no cabe.

**Por qué 60 s es aceptable aquí:**

1. **Las escrituras de la API no esperan al TTL.** Cada entrada, salida o ingrediente nuevo limpia la caché, y la siguiente lectura es fresca. Una prueba lo comprueba: tras una salida de 20 kg, la siguiente lectura ya muestra 30 en lugar de 50. El TTL solo cubre las escrituras **fuera de la API**: scripts de semilla o cambios en el panel de Supabase, que hoy son excepcionales.
2. **El stock de una salida nunca sale de la caché.** `POST /orders/outbound` recalcula el stock en la base con `SELECT ... FOR UPDATE` y responde 400 si no alcanza. Una prueba lo demuestra: con un stock cacheado de 50, si fuera de la API se consumen 45, una salida de 10 se rechaza. En el peor caso, el usuario ve un número viejo y un mensaje con el disponible real; nunca un stock negativo.
3. **El panel de stock del formulario de salida** usa `GET /products/{id}`, que no se cachea (§6.3). El dato que el usuario ve justo antes de escribir la cantidad es siempre el de la base.

**Por qué no más:** con 5 minutos, un ajuste externo podría tardar demasiado en verse en la vista principal del inventario. **Por qué no menos:** con 5–10 s, la caché apenas acertaría entre la apertura de la lista y la de un formulario, que es justo el recorrido habitual.

### 5.2 Historial: 5 minutos

El historial es de consulta: nadie decide una salida a partir de él. Si una orden se escribe fuera de la API, puede tardar hasta 5 minutos en aparecer, y eso no tiene consecuencias operativas. Cada recarga evitada ahorra ~1,3 s y 5,8 MB de serialización. Las órdenes registradas por la API aparecen al momento, porque invalidan la caché.

### 5.3 La invalidación solo ve su propio proceso

La caché vive en el proceso de la API. Es correcta con un solo proceso de uvicorn, que es el despliegue actual, en local y en Docker. Con varios workers o instancias, cada uno tendría su copia, y una escritura solo limpiaría la del worker que la atendió: los demás servirían datos viejos hasta el TTL. Ese es otro motivo para que los TTL sean cortos. Las alternativas están en §7.

## 6. Qué no se cacheó y por qué

### 6.1 `GET /auth/me` — el más frecuente, a propósito sin caché

Es la llamada más frecuente: el backoffice la hace en cada carga de una página protegida, para validar la sesión. Aun así:

- **Cuesta 0,9 ms.** No hay nada que ahorrar.
- **Son datos de sesión.** Una caché compartida sería una fuga de datos. Una caché por usuario sería correcta en cuanto a privacidad, pero **retrasaría la revocación**: este endpoint es el que detecta una cuenta desactivada (403 `inactive_user`) o un token anterior a un cambio de contraseña (401 `session_revoked`). Cachearlo dejaría una sesión revocada viva durante todo el TTL.

### 6.2 Perfiles y usuarios

`/profiles/*` y `/users/*` son datos personales y cuestan ~1 ms, porque `auth-db.json` es un archivo pequeño y aparte. Cachearlos exigiría claves por usuario a cambio de nada, y añadiría el riesgo de servir un perfil a quien no es su dueño.

### 6.3 `GET /inventory/products/{id}` — fresco a propósito

Cuesta lo mismo que el listado (~90 ms), pero se pide una vez cada vez que se elige un ingrediente en el formulario de salida. Es el stock que el encargado lee justo antes de escribir la cantidad: mantenerlo siempre fresco tiene más valor que ahorrar 90 ms en una acción puntual. Además, añadiría una clave por ingrediente con la misma invalidación, sin un acierto frecuente que la compense.

### 6.4 Todo lo que vive en TinyDB (incidencias y proveedores)

Con volumen, `GET /incidents` cuesta 234 ms, `/incidents/summary` 43 ms y `/suppliers` 33 ms: cumplirían los umbrales. Se descartaron porque **la caché ocultaría la causa en lugar de resolverla**:

- **La causa es el almacenamiento, no cada endpoint.** TinyDB vuelve a leer y parsear los 5,2 MB del archivo en cada consulta. Por eso los 15 proveedores, que no crecieron, pasaron de 2,4 a 33 ms. Habría que cachear cada lectura de cada dominio para tapar un único problema.
- **La solución ya está decidida.** Migrar `incidents` y `suppliers` a PostgreSQL (riesgo "Base de datos a medio migrar" de `memory-bank/progress.md`). Después de la migración habría que volver a medir con el middleware.
- **La invalidación sería más frágil.** `scripts/seed_incidents.py` escribe en el mismo archivo desde otro proceso, con la API arrancada, y la caché nunca lo vería.

### 6.5 Escrituras, autenticación y entradas únicas

- **`POST`, `PUT`, `PATCH` y `DELETE`:** nunca se cachean. Las del inventario son las que invalidan.
- **`login`, `change-password` y `reset-password`:** cuestan ~250 ms por bcrypt, y ese coste es una defensa contra la fuerza bruta.
- **`POST /incidents/analyze`:** cada CSV es distinto.
- **`GET /incidents/results/export`:** ya sirve un resultado que está en memoria.

### 6.6 Frontend

- **Ingredientes y proveedores** (103 y 104 ms, 3 074 y 371 nodos): no tienen nada que diferir ni memoizar.
- **El resto de los cálculos derivados** (recuentos de proveedores activos, niveles de stock de 156 ingredientes): son triviales. `mergeOrders` (12,5 ms) ya se ejecuta una sola vez por carga, en el cargador de `useOrders`, así que memoizarlo no aporta nada.

## 7. Límites y trabajo futuro

- **Paginar en la API.** `GET /inventory/orders` y `GET /incidents` siguen devolviendo todo. La caché acelera las peticiones repetidas y "Mostrar más" acelera el render, pero el primer fallo (1,1 s) y la descarga siguen creciendo con los datos. Es la solución de fondo y exige cambiar el contrato con el backoffice.
- **Invalidación entre procesos.** Cuando la API escale a varios workers:
  1. **Redis compartido.** Todos los workers ven la misma caché, y una invalidación los alcanza a todos. Es la evolución natural.
  2. **`LISTEN/NOTIFY` de PostgreSQL.** Con triggers en las tres tablas, cubriría también los scripts y el panel de Supabase. Requiere migraciones (hoy solo hay `create_all`) y una conexión directa: el pooler de transacciones no admite `LISTEN`.
  3. **Validar contra una marca de versión barata** (por ejemplo, el id máximo de las órdenes): solo compensa en `/orders` (90 ms frente a 1,3 s). En `/products` anula la ganancia, porque su coste ya es ese viaje.
- **Migrar TinyDB a PostgreSQL** (§6.4) y volver a medir.
- **Profiler de React:** el beneficio del `useMemo` está estimado con mediciones del cálculo, no con un perfil de renders en React DevTools.

**Cambio posterior (cola de tareas, ticket #DEV-55, 2026-11-25).** El reporte técnico de telemetría, posterior a este informe, tenía su propia caché en memoria de 60 s por combinación de parámetros (`report_cache`, con `X-Cache`). Al convertirse en tarea asíncrona (`POST /telemetry/report` → `202` y `GET /tasks/{task_id}`), esa caché se retira: la sustituye la deduplicación en Redis, que con la misma clave (los parámetros recibidos, `now` para el que falte) devuelve el mismo `task_id` mientras la tarea vive y 60 s después de terminar bien. Es la primera pieza compartida entre procesos, en la línea de la opción 1 de arriba. Las cachés del inventario, de los locales y del reporte semanal no cambian. Detalle en `services/brasaland-api/README.md`, sección "Telemetry technical report".

## 8. Verificación

| Comprobación | Resultado |
|---|---|
| API: `uv run pytest` | **952 pruebas** superadas (926 al empezar; 5 del middleware, 8 de `TTLCache`, 13 de la caché por HTTP) |
| Caché por HTTP (`tests/integration/test_inventory_cache.py`) | `MISS`→`HIT` con los mismos bytes; JSON igual al del contrato; una entrada por país; invalidación con cada escritura; una salida rechazada no invalida; la validación de stock no usa la caché; 401 sin token con la caché llena; los mismos bytes para otro usuario; una escritura fuera de la API solo se ve al expirar el TTL |
| Seeder (`scripts/test_seed_volume.py`) | 10 pruebas sobre bases temporales (sin stock negativo, coherencia país–local–proveedor, idempotencia y `--clear` sin tocar los datos reales) |
| Backoffice | `tsc --noEmit` ✅, `lint` ✅, **Jest 180** (170 al empezar; 5 de `useShowMore` y 5 de `filterOrders`), `next build` ✅ |
| Prueba funcional en Chrome (sin escrituras) | 50 filas al entrar y 100 tras "Mostrar más"; vuelta a 50 al cambiar un filtro (historial y gestor); "platano" encuentra "Plátano"; los modales descargan su chunk al abrirse; sin errores de consola |

**Cómo reproducirlo:**

1. Desde la raíz, con la API parada, cargar el volumen: `uv run --project services/brasaland-api --env-file services/brasaland-api/.env python scripts/seed_volume.py`.
2. Arrancar la API con `--no-access-log` y leer las líneas de `api.timing`.
3. Comprobar la caché con `curl -i` a `/api/v1/inventory/products` con un token: la cabecera `X-Cache` pasa de `MISS` a `HIT`.
4. Retirar el volumen con `--clear`.
