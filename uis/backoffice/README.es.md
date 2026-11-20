# Backoffice de Brasaland

Aplicación interna desde la que el personal de Brasaland accede a sus herramientas en un solo lugar.

Responde a la necesidad de sistemas internos modernos descrita en `CONTEXT.md`. Sus primeras herramientas apoyan la selección de Personas y Cultura y la revisión de la lógica de negocio.

> _Versión en inglés: [README.md](./README.md)._

## Stack

Next.js 16 (App Router), React 19, TypeScript y Tailwind CSS 4. Es un proyecto independiente: no comparte layout con `uis/website`.

## Cómo ejecutarlo

Copia `.env.example` como `.env.local` e indica las URL de las API:

```bash
NEXT_PUBLIC_API_BASE_URL=<url-base-de-la-api>     # API del tracker
API_BASE_URL=http://localhost:8000/api/v1         # API de Brasaland (services/brasaland-api)
NEXT_PUBLIC_TELEMETRY_ENDPOINT=http://localhost:8000/telemetry/events  # receptor de telemetría
NEXT_PUBLIC_TELEMETRY_ENVIRONMENT=development     # entorno de los eventos
```

Las herramientas que usan la API de Brasaland necesitan que esté arrancada; las instrucciones están en [`services/brasaland-api/README.es.md`](../../services/brasaland-api/README.es.md).

Después ejecuta:

```bash
npm install
npm run dev     # http://localhost:3001
npm run lint
npm run build
npm test                # pruebas unitarias con Jest (__tests__/)
npm run test:coverage   # lo mismo, con cobertura (informe en coverage/)
npm run telemetry:catalog  # regenera lib/telemetry/catalog.ts tras cambiar docs/telemetry/event-schemas.json
```

`npm install` enlaza `@repo/brasa-core` desde `packages/brasa-core`, así que hay que ejecutarlo después de clonar el repositorio.

Las pruebas de Jest cubren la lógica de autenticación de `lib/auth/` (`__tests__/auth/`, ticket AUTH-088), las utilidades `lib/format.ts`, `toUserMessage` y `readJson` (`__tests__/utils/`, ticket FE-019) y la sección de inventario (`__tests__/inventory/`, ticket BRD-0512): llamadas de `lib/inventory.ts` con `fetch` simulado, niveles de stock, validación de los formularios y unión del historial. El servicio de telemetría tiene las suyas en `__tests__/telemetry/` (cola, envío, envelope, sesión, validación y catálogo). Cada carpeta se ejecuta sola con `npm test -- __tests__/auth`, `__tests__/utils`, `__tests__/inventory` o `__tests__/telemetry`. Qué prueba cada archivo y su cobertura están en [`services/brasaland-api/TESTING.es.md`](../../services/brasaland-api/TESTING.es.md#pruebas-del-backoffice-jest) y en su sección de FE-019.

## Sesión

Todas las vistas exigen sesión salvo `/login`, `/register` (ticket AUTH-02), `/forgot-password` y `/reset-password` (ticket AUTH-03). El website público (`uis/website`) no se ve afectado.

| Ruta | Vista |
|---|---|
| `/login` | Email y contraseña (con botón para mostrarla). Guarda el token y vuelve a la ruta de `?next=` (solo rutas internas), o a `/`. Muestra un aviso si la sesión caducó (`?reason=expired`), si la cuenta está desactivada (`?reason=inactive`) o tras restablecer la contraseña (`?reset=success`). Tiene el enlace "¿Olvidaste tu contraseña?" |
| `/register` | Email, contraseña (con botón para mostrarla) y perfil opcional (nombre y apellido, teléfono y dirección). Llama a `POST /users` y luego a `POST /auth/login`. Los errores de la API se muestran junto a cada campo |
| `/forgot-password` | Email. Llama a `POST /auth/forgot-password` y muestra siempre "Si esa dirección está registrada, recibirás un enlace en breve", sin revelar si la cuenta existe. Tras el envío, el formulario queda desactivado. Si la petición no llega a la API (sin conexión), muestra el error y deja reintentar |
| `/reset-password` | Abre el enlace del correo (`?token=`). Comprueba el enlace al abrirse (`POST /auth/reset-password/validate`): si no es válido, caducó o ya se usó, muestra el error y "Solicitar un nuevo enlace". Si sirve, pide la contraseña nueva y su confirmación (deben coincidir antes de llamar a la API), llama a `POST /auth/reset-password` y vuelve a `/login?reset=success`. No envía la URL con el token como `Referer` (`referrer: no-referrer`) |
| `/account/profile` | Requiere sesión. Muestra el email y el perfil (de `GET /auth/me`) y permite editar nombre y apellido, teléfono y dirección con `PUT /profiles/me`. Solo envía los campos cambiados; un campo vacío se borra. Al guardar se actualiza el nombre de la cabecera. Enlaza a `/account/change-password` |
| `/account/change-password` | Requiere sesión. Contraseña actual, nueva y confirmación (deben coincidir antes de llamar a la API). Llama a `POST /auth/change-password`: con éxito guarda el token nuevo que devuelve la API (las sesiones anteriores dejan de valer), vacía el formulario y muestra "Contraseña actualizada."; una contraseña actual incorrecta (400) se muestra junto a ese campo |

Cómo funciona:

- **Token:** se guarda en `localStorage` (`lib/auth/token.ts`). El cliente común `lib/api-client.ts` lo envía como `Authorization: Bearer <token>` al intermediario, que lo reenvía a la API.
- **Protección:** las vistas protegidas viven en el grupo de rutas `app/(protegido)/`, y toda página creada ahí queda protegida. Su layout usa `SessionProvider`, un guard en el cliente:
  - sin token, redirige a `/login?next=<ruta>`;
  - con token, comprueba la sesión con `GET /auth/me` y no muestra nada hasta tenerla.

  No se usa `proxy.ts`, porque el servidor no puede leer `localStorage`. `useSession()` da acceso al usuario, a `refresh` y a `logout`.
- **Fin de sesión:** ante un 401, o un 403 `inactive_user`, el cliente común borra el token y redirige al login con el motivo. "Cerrar sesión" (en la cabecera) borra el token y lleva a `/login`.
- **Varias pestañas:** si el token desaparece en otra pestaña, esta redirige al login; si cambia, recarga el usuario.

## Herramientas

| Ruta | Herramienta | Datos |
|---|---|---|
| `/` | Portada con las herramientas agrupadas en las mismas secciones que el menú (Inventario, Proveedores, Incidencias y Herramientas), una tarjeta por herramienta | `lib/tools.ts` |
| `/talento` | Talent Pipeline Tracker: candidatos, status, stage y notas. El formulario de candidato se carga de forma diferida (`next/dynamic`) al abrirlo | API REST |
| `/incidencias` | Análisis de incidencias: sube el CSV de Operaciones, muestra el resumen y los registros inválidos con su motivo, y descarga `results.csv` | API de Brasaland, a través del intermediario |
| `/gestor-incidencias` | Gestor de incidencias: resumen (totales por estado, categoría, origen y sede, de `GET /incidents/summary`) y listado con filtros por `status`, `origin` y `branch`, de la más reciente a la más antigua. Cada bloque tiene su propia carga y su error con "Reintentar", así que un fallo del resumen no rompe el listado. Lista vacía y "sin resultados con los filtros" tienen su mensaje. Cada incidencia cambia de estado desde el listado (solo las transiciones válidas): el cambio se ve al momento y, si la API lo rechaza o falla, vuelve al estado anterior y avisa. Las fechas se muestran en UTC, porque el histórico se cargó como medianoche UTC. El listado pinta 50 incidencias y 50 más con "Mostrar más"; vuelve a 50 al cambiar un filtro, no al cambiar un estado | API de Brasaland (dominio `incidents`, TinyDB), a través del intermediario |
| `/gestor-incidencias/nueva` | Registrar incidencia (gestor de incidencias centralizado): título, descripción, categoría, origen y sede, con campos grandes para tablet. Valida los obligatorios antes de enviar; con `origin = branch` resalta la sede; el desplegable de sedes muestra los nombres del briefing ("Medellín Centro"). Durante el envío, el botón queda deshabilitado con un indicador de carga; los errores de la API aparecen junto a su campo y, tras el éxito, el formulario se limpia y confirma. Toda incidencia nueva empieza en `open` | API de Brasaland (dominio `incidents`, TinyDB), a través del intermediario |
| `/proveedores` | Directorio de proveedores: listado de activos y suspendidos, filtros por país y categoría, alta, actualización de tarifa y activar o suspender. El formulario de alta se carga de forma diferida (`next/dynamic`) al abrirlo | API de Brasaland (dominio `suppliers`, TinyDB), a través del intermediario |
| `/inventario/ingredientes` | Inventario (Hito 5): ingredientes con SKU, categoría, país, unidad y stock actual, con su nivel (sin stock, bajo o saludable; umbrales por unidad en `lib/inventory-stock-level.ts`) y una leyenda. Cada fila abre la entrada o la salida con el ingrediente elegido (`?ingredient_id=`). `/inventario` redirige aquí | API de Brasaland (dominio `inventory`, Supabase), a través del intermediario |
| `/inventario/ordenes/entrada` | Registrar entrada: local (los 14 del catálogo, con su nombre y su país), ingrediente (solo los del país del local; por nombre, con SKU y unidad), cantidad, proveedor (de los activos del directorio con el país y la categoría del ingrediente; si no hay ninguno, un aviso enlaza al directorio) y coste en la moneda del local. Elegir un local de otro país quita el ingrediente y lo avisa. Valida antes de enviar; los errores de la API aparecen junto a su campo o en un aviso; tras el éxito confirma y se limpia | Ídem |
| `/inventario/ordenes/salida` | Registrar salida: local, ingrediente (solo los del país del local), cantidad y motivo (`consumption` o `waste`). Muestra el stock actual al elegir el ingrediente, avisa sin bloquear si la cantidad lo supera y muestra el 400 de stock insuficiente junto a la cantidad | Ídem |
| `/inventario/ordenes` | Historial de órdenes, solo lectura: entradas y salidas juntas, de la más reciente a la más antigua, con tipo, ingrediente, cantidad, proveedor o motivo, local (por su nombre), fecha y usuario (`user_uuid`, con "Tú" en las propias). Filtros por tipo e ingrediente (nombre o SKU, sin distinguir tildes), aplicados en el navegador y memoizados. Pinta 50 órdenes y 50 más con "Mostrar más" | Ídem |
| `/funciones` | Pruebas manuales de filtros, búsquedas, reportes y validaciones | Datos de ejemplo de `@repo/brasa-core` |
| `/telemetria` | Telemetría técnica (reporte técnico, solo administradores): el período del reporte y un bloque por métrica. `events_per_day`, con una barra por día apilada por nivel; `error_rate_by_type`, `api_latency_by_route` (con una barra de la media) y `auth_failure_rate`, en tablas. Dos fechas opcionales en UTC, las dos incluidas (el fin se envía como el día siguiente, porque la API lo toma como exclusivo) y "Últimos 7 días". Quien no es admin ve "Solo los administradores pueden ver el reporte técnico." Barras con Tailwind, sin librería de gráficos | `GET /telemetry/report` de la API, a través de `app/api/telemetry/report/route.ts` |

## Añadir una herramienta

1. Crea su ruta en `app/(protegido)/<herramienta>/`, para que exija sesión. El grupo no cambia la URL.
2. Pon sus archivos propios en `components/<herramienta>/` y `lib/<herramienta>/`. Las piezas reutilizables van directamente en `components/`.
3. Añade una entrada en `lib/tools.ts`, dentro de su sección de `toolSections`. La portada y la navegación se generan desde esa lista: una sección con una sola herramienta es un enlace directo en la cabecera; con varias, un desplegable (`components/NavDropdown.tsx`).

Las áreas internas, incluida la formación, se incorporan aquí como herramientas, no como aplicaciones aparte. Más adelante, cada entrada de `lib/tools.ts` podrá declarar el permiso que necesita y la lista se filtrará con `GET /auth/me`. Ese filtro solo afectará a la interfaz: la autorización real está en la API.

Las llamadas a la API de Brasaland se hacen con `apiJson` o `apiFetch` de `lib/api-client.ts`, que añaden el token, convierten los errores en `ApiError` (`status`, `code`, `message`, `details` por campo) y cierran la sesión ante un 401.

## Telemetría

El backoffice captura eventos de uso con un servicio propio, `lib/telemetry/` ([plan de telemetría](../../docs/telemetry/telemetry-plan.md), sección 13). **Todo el tracking pasa por una única función**:

```ts
import { track } from "@/lib/telemetry";

track("page_viewed", { route: "/inventario/ordenes", navigation_type: "client" });
```

- **Quien llama solo pasa el tipo y las propiedades.** El servicio añade el envelope: `eventId` (UUID generado al capturar), `timestamp` de la captura, `sessionId`, `userId`, `schemaVersion` del esquema de ese evento, `requestId`, `source: "browser"` y `environment`.
- **Allowlist.** `track()` comprueba cada evento contra `lib/telemetry/catalog.ts`, que se genera desde `docs/telemetry/event-schemas.json` (`npm run telemetry:catalog`). Un tipo desconocido, una propiedad obligatoria ausente o una clave fuera del allowlist hacen que el evento se descarte, con un aviso en la consola en desarrollo.
- **Envío por lotes.** Los eventos se acumulan en memoria y salen a `NEXT_PUBLIC_TELEMETRY_ENDPOINT` cada 10 segundos o al llegar a 20, lo que ocurra primero. Si el envío falla, se reintenta 3 veces (esperas de 1, 2 y 4 s) y después el lote se descarta. Al ocultar o cerrar la pestaña, lo pendiente sale con `navigator.sendBeacon`. Sin la variable, la telemetría está desactivada.
- **Sesión.** `sessionId` se crea al iniciar sesión y se guarda en `sessionStorage` (uno por pestaña). `userId` es el `sub` del token (el UUID de la cuenta, nunca el email). Sin sesión, los dos son `null`.
- **Correlación.** `apiFetch` envía un UUID nuevo en `X-Request-Id` en cada llamada; el intermediario lo reenvía y la API lo escribe en su log. Los eventos que nacen de una respuesta de la API llevan ese `requestId`, que la capa de datos fija con `withRequestId()` (`lib/telemetry/request-context.ts`).
- **Dónde se instrumenta.** Nunca en los componentes, sino en la capa de datos:
  - `lib/inventory.ts` emite las métricas obligatorias de las órdenes al recibir el 201: `inbound_order_created`, `ingredient_price_variance_detected` (con el historial de `GET /inventory/orders`), `outbound_order_created` o `stock_waste_registered` según el motivo, y `stock_threshold_triggered` al cruzar el umbral de stock bajo. Los cálculos están en `lib/telemetry/inventory-events.ts`;
  - `lib/api-client.ts` pasa cada llamada a `lib/telemetry/api-events.ts`: `api_latency_recorded` (siempre las lentas y las de error, 1 de cada 10 del resto) y, en los errores, `api_error_returned` (4xx), `api_connection_failed` (502, 504 o 500 del intermediario), `order_validation_failed`, `direct_stock_edit_rejected` cuando la API rechaza un cambio directo del stock (el 405 de "Ajustar stock" o un 422 por `current_stock`), `session_expired` y `auth_token_rejected` (401 de sesión, uno por token cada 60 s) y `password_reset_link_rejected`;
  - `lib/proveedores/api.ts`, `lib/gestor-incidencias/api.ts` y `lib/incidencias/api.ts` emiten `supplier_created`, `supplier_rate_updated`, `supplier_status_changed`, `incident_created`, `incident_status_changed`, `incident_transition_rejected` e `incident_report_analyzed` (cálculos en `lib/telemetry/business-events.ts`); `lib/inventory.ts` emite también `outbound_order_rejected`;
  - los formularios de entrada, salida, incidencia, proveedor, login y registro usan `useFormTelemetry` (`form_validation_failed` y `form_abandoned`, solo con nombres de campo), y el historial, el gestor y el directorio, `useListFilterTelemetry` (`list_filter_applied`) y `useShowMore` (`list_page_extended`);
  - `lib/auth/api.ts` y `SessionProvider` emiten la autenticación: `login_failed` (`invalid_credentials`, `inactive_user` o `network_error`, nunca el email ni la contraseña), `login_succeeded` (al validar la sesión, con el rol), `logout_completed`, `user_registered`, `password_reset_completed` y `password_changed`;
  - `components/telemetry/TelemetryRoot.tsx`, en el layout raíz, emite `page_viewed` en cada vista, `frontend_error_captured` para `window.onerror` y `unhandledrejection` (las pantallas `error.tsx` y `global-error.tsx` lo emiten con `useReportBoundaryError`) y recoge Web Vitals con `useReportWebVitals`: LCP, CLS e INP salen en un `page_performance_recorded` por carga, al ocultar la pestaña y antes del `sendBeacon` (`lib/telemetry/lifecycle.ts`).
- **Receptor.** La URL apunta directamente a la API (`http://localhost:8000/telemetry/events`), sin pasar por el intermediario: es la única llamada del navegador a otro origen, y la API admite CORS solo para ella.

## Estructura

- `app/`: layout raíz (sin cabecera) y dos grupos de rutas:
  - `(protegido)/`: portada y una carpeta por herramienta, con el guard de sesión;
  - `(publico)/`: `login/` y `register/`, con una cabecera sin navegación.
- `app/api/[...path]/route.ts`: intermediario (BFF) hacia la API de Brasaland. El reenvío está en `lib/bff/proxy.ts`, que comparte con `app/api/telemetry/report/route.ts`: el reporte técnico de telemetría, que la API sirve fuera de `/api/v1`, se reenvía al origen de `API_BASE_URL` (`http://localhost:8000/telemetry/report`). Next.js elige esa ruta antes que el catch-all.
  - Reenvía `GET`, `POST`, `PUT`, `PATCH` y `DELETE` de `/api/<ruta>` a `API_BASE_URL/<ruta>`, con las cabeceras `Content-Type`, `Accept`, `Authorization` y `X-Request-Id`, sin aplicar lógica. De la respuesta copia `Content-Type`, `Content-Disposition`, `X-Request-Id` y `X-Cache`.
  - La URL de la API se queda en el servidor y no hace falta CORS.
  - Si falta la variable responde 500 (`api_not_configured`); si la API no responde, 502 (`api_unavailable`); si tarda más de 15 segundos, corta la petición y responde 504 (`api_timeout`). En los tres casos el usuario recibe un mensaje genérico, y el log del servidor registra una línea `[BFF]` con el método, la ruta (sin query) y la causa; nunca cabeceras ni cuerpo.
- `components/`:
  - componentes base reutilizables, entre ellos `PasswordField`, con botón para mostrar la contraseña, `FileDropzone`, para cualquier herramienta que reciba archivos, y `TextAreaField`. `FormField`, `TextAreaField` y `LabeledSelect` admiten `size="lg"` para formularios táctiles;
  - `auth/` (`SessionProvider`, `ProtectedShell`, `AccountMenu` y los formularios de login, registro y recuperación de contraseña) y `account/` (perfil y cambio de contraseña);
  - `talento/`, `funciones/`, `incidencias/`, `gestor-incidencias/`, `proveedores/`, `inventario/` y `telemetria/` (la vista del reporte técnico; `telemetry/` es la captura de eventos).
- `hooks/`: hooks personalizados, entre ellos `useSession` y `useShowMore` (listas largas por partes).
- `lib/`: `tools.ts`, `format.ts`, `api-client.ts`, `auth/`, `telemetry/` (servicio de telemetría; ver [Telemetría](#telemetría)), `bff/proxy.ts` (reenvío del intermediario), `telemetry-report.ts` (cliente y formato del reporte técnico) y una carpeta por herramienta. El inventario usa archivos `lib/inventory*.ts`: `inventory.ts` es su módulo de integración, el único que llama a `/api/inventory/...`.
- `scripts/generate-telemetry-catalog.mjs`: genera `lib/telemetry/catalog.ts` desde `docs/telemetry/event-schemas.json`.
- `types/`: tipos de la API (`api.ts` para los errores y `auth.ts` para usuarios y perfiles).

## Limitaciones conocidas

- **El token vive en `localStorage`:** lo exige el ticket AUTH-02, pero un script inyectado en la página podría leerlo. La propuesta de arquitectura (5.2) preveía una cookie inaccesible desde JavaScript.
- **Registro abierto:** `/register` y `POST /users` son públicos, así que cualquiera puede crearse una cuenta `user` y entrar. Aún no hay permisos por herramienta.
- **La comprobación de sesión es del navegador:** el servidor entrega las vistas protegidas sin su contenido, y este solo aparece tras validar el token con la API. La protección real de los datos está en la API.
- **`/funciones` es temporal:** prueba las reglas de `@repo/brasa-core`, un paquete transitorio. Cuando esas reglas pasen al backend, debe retirarse o llamar a la API. No añadas cálculos de negocio a los frontends.
- **`/incidencias` descarga el último análisis de la API:** se guarda en memoria, así que si la API se reinicia hay que volver a subir el archivo, y si dos personas analizan a la vez, se descarga el más reciente.
- **`/proveedores` escribe en la base local de la API:** las altas y los cambios de tarifa o estado se guardan en `services/brasaland-api/storage/brasaland-db.json`. Para volver a los datos iniciales, borra ese archivo y reinicia la API. La interfaz no ofrece borrar proveedores: el flujo habitual es suspenderlos.
- **`/inventario` escribe en la base de la API:** con la API configurada contra Supabase, cada entrada o salida cambia el stock real y no se puede borrar (se corrige con una orden compensatoria). Para probar, arranca la API con una `DATABASE_URL` temporal (por ejemplo, SQLite). El stock de la salida se refresca al elegir el ingrediente y tras cada envío, no en tiempo real: la API aplica la regla con el stock del momento.
- **Altura de la cabecera:** `FilterBar` depende de su altura fija (57 px en móvil y 89 px desde `md`). Desde `xl`, la cabecera muestra el menú por secciones; por debajo no cabe junto a la cuenta, así que se usa un menú hamburguesa (`components/MobileNav.tsx`) cuyo panel se superpone a la página bajo la cabecera, sin cambiar su altura. "Mi perfil" y "Cerrar sesión" se muestran solo como iconos en todos los tamaños; en escritorio, un tooltip (`components/Tooltip.tsx`) muestra el nombre del usuario (o su email) y "Cerrar sesión" al pasar el ratón o llegar con el teclado.
- **API compartida:** el tracker usa una API de playground compartida, así que evita escrituras de prueba. Esa API es de terceros y no recibe el token de sesión.
- **Tras mover rutas, `tsc` puede fallar con tipos antiguos de `.next`:** se arregla borrando `.next`, que es un artefacto generado.
