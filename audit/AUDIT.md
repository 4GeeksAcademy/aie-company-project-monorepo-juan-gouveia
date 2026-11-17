# Auditoría de rendimiento — website y backoffice

Medición inicial, problemas identificados con su causa raíz y análisis de refactorización de los dos frontends de Brasaland: `uis/website` (sitio corporativo) y `uis/backoffice` (panel interno). Las correcciones aplicadas y su impacto están en [`REPORT.md`](REPORT.md).

## 1. Método

### Entorno

| Elemento | Valor |
|---|---|
| Modo | Producción: `npm run build` + `npm run start` en cada app, fuera de Docker (el contenedor de desarrollo usa `next dev`, que no sirve para medir) |
| Website | `http://localhost:3000`: Next.js 16.3.5, React 19.2.8; páginas estáticas (`○`) |
| Backoffice | `http://localhost:3001`: Next.js 16.3.5, React 19.2.8; vistas protegidas que cargan sus datos en el cliente a través del BFF (`/api/[...path]`) |
| API | `services/brasaland-api` en el puerto 8000 con Uvicorn, sin `--reload` |
| Navegador | Chrome 157 |
| Lighthouse | **13.5.0**, la versión que trae DevTools en Chrome 157, tanto en DevTools como en el CLI |

### Condiciones

- **Perfiles de Lighthouse:**
  - móvil: Moto G Power emulado (412×823, DPR 1,75), red 4G lenta simulada (RTT 150 ms, 1,6 Mbps) y CPU ×4;
  - escritorio: el preset `desktop` de Lighthouse.
- **Estado:** caché fría (un perfil de Chrome nuevo en cada ejecución) y sin extensiones.
- **Backoffice:** se mide con la sesión iniciada, con una cuenta temporal de rol `user` creada para la auditoría. La sesión es un JWT en `localStorage`; en DevTools se desmarca "Clear storage" y en el CLI el token se escribe antes de medir, sin cargar ninguna página de la app.
- **Categorías:** Performance, Accessibility, Best Practices y SEO. Se excluye **Agentic Browsing**, que aparece en Lighthouse 13: evalúa si un agente de IA puede usar la página, no el rendimiento ni la experiencia de las personas.

### Evidencia

- **Capturas** de DevTools en [`before/`](before/) (`<app>-<ruta>-<modo>.png`).
- **Números:** mediana de **3 ejecuciones** de Lighthouse CLI con las mismas condiciones. Las skills de la auditoría piden mediana y rango porque una sola ejecución varía.
  - El JSON de la mediana está en `before/<app>-<ruta>-<modo>.json` (se puede abrir en el [visor de Lighthouse](https://googlechrome.github.io/lighthouse/viewer/)).
  - Las 3 ejecuciones están en `before/<app>-<ruta>-<modo>.summary.json`.
- **Informes exportados de DevTools:** los dos de móvil están en `before/devtools-website-*-mobile.json`. Sirvieron para conciliar las dos herramientas (ver más abajo).

**Por qué se fijó la versión de Lighthouse.** La primera tanda del CLI usó Lighthouse 13.6.0 y daba un LCP en móvil de 0,76 s, frente a los 2,4 s de DevTools. El elemento LCP, la emulación y la limitación de red y CPU eran idénticos. En los dos casos el LCP *observado* coincidía con el FCP (~150–250 ms), así que la diferencia estaba en la *estimación simulada* (Lantern), que cambia entre versiones. Con la 13.5.0 el CLI reproduce los valores de DevTools (2,46–2,55 s). Conclusión: las puntuaciones de Lighthouse solo son comparables con la misma versión. Por eso el "antes" y el "después" usan la 13.5.0.

### Skills de agente

Se instalaron dos skills de [`addyosmani/web-quality-skills`](https://github.com/addyosmani/web-quality-skills) (commit `afa8da9`, licencia MIT), solo para el proyecto y sin commit:

- **`core-web-vitals`**: umbrales de LCP, CLS e INP, referencias de diagnóstico por métrica (`references/LCP.md` y `references/CLS.md`) y correcciones habituales en Next.js.
- **`performance`**: método basado en evidencia (`references/MEASUREMENT.md`), presupuestos de recursos y optimización de imágenes, fuentes y JavaScript.

Las dos recomiendan grabar trazas con Chrome DevTools MCP. Como no estaba disponible, se usó la alternativa que proponen: Lighthouse CLI con la versión compatible, JSON guardados y mediana de 3.

**Clasificación de los hallazgos.** Las skills no etiquetan nada como "requerido"; separan las *métricas que fallan* (medidas) de las *hipótesis* (inspección del código sin medición). Siguiendo ese criterio, aquí:

- **Requerido:** el hallazgo está ligado a una métrica que falla o queda en el umbral, o a una auditoría de Lighthouse que falla, y hay evidencia de su causa.
- **Sugerencia:** sale del checklist de las skills, o tiene un impacto medido marginal; se documenta, pero no se corrige si eso exige reestructurar.

## 2. Puntuaciones iniciales

Mediana de 3 ejecuciones (Lighthouse 13.5.0). El rango aparece cuando las 3 ejecuciones no coinciden.

| Página | Modo | Performance | Accessibility | Best Practices | SEO |
|---|---|---|---|---|---|
| website `/` | escritorio | 100 | 100 | **96** | 100 |
| website `/` | móvil | **97** (97–98) | 100 | **96** | 100 |
| website `/registro` | escritorio | 100 | 100 | **96** | 100 |
| website `/registro` | móvil | 99 | 100 | **96** | 100 |
| backoffice `/` | escritorio | 100 | 100 | 100 | 100 |
| backoffice `/gestor-incidencias` | escritorio | 99 (**90**–99) | 100 | 100 | 100 |

| Página | Modo | FCP | LCP | TBT | CLS | Speed Index | TTFB* |
|---|---|---|---|---|---|---|---|
| website `/` | escritorio | 0,21 s | 0,54 s | 0 ms | 0 | 0,24 s | 125 ms |
| website `/` | móvil | 0,76 s | **2,54 s** (2,46–2,55) | 39–48 ms | 0 | 0,76 s | 455 ms |
| website `/registro` | escritorio | 0,21 s | 0,48 s | 0 ms | 0 | 0,21 s | 124 ms |
| website `/registro` | móvil | 0,76 s | 2,21 s (2,14–2,23) | 25–38 ms | 0 | 0,76 s | 454 ms |
| backoffice `/` | escritorio | 0,21 s | 0,65 s | 0 ms | 0 | 0,21 s | 125 ms |
| backoffice `/gestor-incidencias` | escritorio | 0,21 s | 0,69 s | 0 ms | **0,065 (0,065–0,204)** | 0,21 s | 125 ms |

\* TTFB simulado por Lighthouse (incluye el RTT emulado). El TTFB observado en local es de 5–10 ms.

**Lectura general.** Los dos frontends parten de una base sana: páginas del website prerenderizadas, `next/image` en todas las imágenes, sin fuentes web y sin scripts de terceros. Los problemas son concretos y pocos:

- el CLS del gestor de incidencias es intermitente y llega a "necesita mejorar";
- el LCP en móvil de la home queda en el umbral de 2,5 s;
- Best Practices pierde 4 puntos en todo el website por un único error.

## 3. Problemas identificados

| ID | Frontend | Problema | Métrica | Clasificación | Prioridad |
|---|---|---|---|---|---|
| P1 | Backoffice | El listado se desplaza cuando llega el resumen | CLS hasta 0,204 | Requerido | 1 |
| P2 | Website | El LCP en móvil de la home queda en el umbral | LCP 2,54 s | Requerido | 2 |
| P3 | Website | `/favicon.ico` devuelve 404 | Best Practices 96 | Requerido | 3 |
| P4 | Website | La hoja de estilos bloquea el render | ~155 ms simulados | Sugerencia | — |
| P5 | Website | JavaScript con polyfills antiguos y código sin usar | 14 KB + 49 KB | Sugerencia | — |

### P1 — CLS intermitente en `/gestor-incidencias` (backoffice)

- **Evidencia:**
  - CLS de 0,065 en 2 de 3 ejecuciones y de 0,204 en la tercera, con Performance en 90;
  - la captura de DevTools da 0,099;
  - la auditoría `layout-shifts` y el insight `cls-culprits` señalan un único nodo desplazado: `section[aria-labelledby="list-heading"]`, la sección del listado.
- **Causa raíz:**
  - `IncidentPanel` pinta dos bloques que cargan por separado: el resumen (`useIncidentSummary` → `GET /incidents/summary`) arriba y el listado (`useIncidents` → `GET /incidents`) debajo.
  - Mientras carga, `IncidentSummaryPanel` solo muestra una línea ("Cargando el resumen...", unos 20 px). Al llegar los datos, esa línea se sustituye por 5 tarjetas de estado y 3 columnas de desglose (8 categorías, 3 orígenes y 16 sedes), unos 600 px.
  - Todo lo que hay debajo, es decir, la sección del listado, baja de golpe. El listado no causa el problema; lo sufre (*victim*, en palabras de la skill).
  - **Por qué es intermitente:** si el resumen llega antes del primer pintado con contenido, no hay desplazamiento visible; si llega después, el listado ya estaba en pantalla y se desplaza. Depende del orden en que respondan las dos peticiones.
- **Skill:** `core-web-vitals` → `references/CLS.md`, sección *Handle dynamic content deliberately*: "allocate a stable container before the content arrives". Checklist: "async components have stable containers".
- **Corrección prevista:**
  - Que el estado de carga del resumen ocupe el mismo espacio que el resumen final. Se puede hacer de forma exacta porque la estructura del resumen no depende de los datos: el número de estados, categorías, orígenes y sedes es fijo y ya está en `lib/gestor-incidencias/labels.ts`.
  - Mientras carga, se pinta la misma cuadrícula con las etiquetas reales y las cifras como marcadores (`—`), en lugar de una línea de texto.
  - No cambia ni el flujo de datos ni la arquitectura.

### P2 — LCP en móvil en el umbral en la home del website

- **Evidencia:**
  - LCP de 2,54 s (2,46–2,55) en móvil, el único Core Web Vital del website fuera de "bueno" (≤ 2,5 s);
  - el elemento LCP es un párrafo de texto de "Nuestra Historia" (`<p class="mb-4 …">`);
  - el LCP observado coincide con el FCP: el texto está en el HTML inicial y se pinta en cuanto llega el CSS. El desglose (`lcp-breakdown-insight`) da TTFB ~6 ms y render delay ~143 ms.
- **Causa raíz:**
  - La estimación simulada de Lighthouse reparte el ancho de banda de la red 4G lenta entre todo lo que se pidió antes del LCP observado. En la home, antes de los ~195 ms del LCP, se piden:
    - ~150 KB de JS del framework;
    - el CSS (5 KB);
    - el logo (5 KB);
    - **la foto de la fachada (15 KB)**;
    - **las 3 fotos de "¿Qué nos hace únicos?" (94 KB)**.
  - La comparación con `/registro` aísla el efecto de las imágenes: tiene el mismo JS de framework, solo el logo como imagen, y un LCP de 2,21 s. Las imágenes que no se ven al cargar añaden **~0,3 s** al LCP de la home.
  - **La fachada se pide de inmediato por `loading="eager"`** (`components/History.tsx`). Tiene sentido en escritorio, donde es el elemento LCP (0,54 s). En móvil está por debajo del pliegue y compite por la red con el CSS y el JS que sí necesita el primer pintado.
  - Las 3 fotos de `Features` usan la carga diferida por defecto de `next/image` (`loading="lazy"`), pero Chrome empieza a descargar las imágenes diferidas a cierta distancia del viewport. Con un viewport de 823 px de alto y la sección justo debajo, entran en ese margen.
- **Skill:**
  - `core-web-vitals` → `references/LCP.md`, tabla *Common issues*: "Large image transfer / resource load" y "Preload only when a trace shows late discovery";
  - `performance` → *LCP image priority*: "Below-fold images: lazy loading".
  - La documentación de `next/image` de Next 16 (`node_modules/next/dist/docs/…/image.md`) también desaconseja `preload` cuando la imagen LCP cambia según el viewport, que es este caso.
- **Corrección prevista:** quitar `loading="eager"` de la fachada para que vuelva a la carga diferida por defecto, y medir los dos modos. Es una hipótesis con riesgo conocido: en escritorio la fachada es el LCP y una imagen LCP diferida puede retrasarlo. Hay margen (0,54 s frente a 2,5 s), pero se medirá. Si empeora el escritorio de forma significativa, se descarta y se documenta.

### P3 — `/favicon.ico` devuelve 404 en el website

- **Evidencia:**
  - Best Practices 96 en las 4 mediciones del website;
  - la auditoría que falla es `errors-in-console`: `Failed to load resource: 404` en `http://localhost:3000/favicon.ico`.
  - El backoffice tiene `app/favicon.ico` y saca 100.
- **Causa raíz:** el website no declara ningún icono, ni `app/favicon.ico` ni `app/icon.*` (convención de metadatos de Next.js). El navegador pide `/favicon.ico` por defecto y recibe un 404, que queda como error en la consola.
- **Skill:** fuera del ámbito de rendimiento de las dos skills. Se clasifica como requerido porque es la única auditoría que falla en Best Practices y tiene una causa clara. Además, el 404 es una petición de red inútil en cada visita.
- **Corrección prevista:** añadir un icono del sitio con la convención de Next.js (`app/icon.*` o `app/favicon.ico`). No basta con silenciar la petición: el sitio corporativo necesita su icono en la pestaña y en los resultados de búsqueda.

### P4 — CSS que bloquea el render (sugerencia)

- **Evidencia:** `render-blocking-insight` marca el único CSS (`/_next/static/chunks/*.css`, 5 KB) con ~155 ms simulados en móvil.
- **Causa raíz:** es la hoja de Tailwind que Next.js enlaza en el `<head>`. Ya es pequeña (5 KB comprimida, muy por debajo de los 14 KB de CSS crítico que propone la skill) y contiene casi solo lo que usa la página.
- **Decisión:** no se corrige. La alternativa sería incrustar el CSS en el HTML (`experimental.inlineCss` de Next.js), una opción experimental que cambia cómo se sirve el CSS en toda la app y deja de aprovechar la caché entre páginas. Eso es un cambio de arquitectura, no una corrección dirigida, y la ganancia es marginal.

### P5 — JavaScript antiguo y sin usar (sugerencia)

- **Evidencia:**
  - `legacy-javascript-insight`: ~14 KB de polyfills (`Array.prototype.at`, etc.) en un chunk del framework;
  - `unused-javascript`: ~49 KB sin usar en la carga inicial;
  - el JS total de la home es ~168 KB transferidos, por debajo del presupuesto de 300 KB de la skill `performance`.
- **Causa raíz:** son los chunks del runtime de Next.js y React; el código propio del website es casi todo de servidor (solo `RegistrationForm` es un componente cliente). Los polyfills vienen de los navegadores objetivo por defecto de Next.js.
- **Decisión:** no se corrige en esta auditoría. Reducir el runtime exigiría cambiar la configuración de compilación o de navegadores objetivo, con riesgo de dejar fuera navegadores que hoy funcionan, para una ganancia que el LCP de `/registro` (2,21 s con el mismo JS) muestra como secundaria.

### Lo que se revisó y no es un problema

- **Imágenes:**
  - todas usan `next/image` con `width`/`height` y `sizes`, así que se sirven en WebP/AVIF a tamaño adaptado (de 5 a 35 KB, cuando los originales pesan hasta 300 KB);
  - reservan su espacio: el CLS del website es 0 en las 4 mediciones.
- **Fuentes:** el website y el backoffice usan fuentes del sistema; no hay `@font-face` ni fuentes externas que bloqueen el texto.
- **TTFB:** el website es estático y el backoffice sirve un HTML estático que se hidrata. En local el TTFB observado es de 5–10 ms; el valor simulado (125–455 ms) solo refleja el RTT emulado.
- **Interactividad (INP/TBT):** no hay datos de campo (CrUX) para `localhost`. En laboratorio, el TBT es de 0 ms en escritorio y de 25–48 ms en móvil, lejos del umbral de 200 ms.
- **Backoffice `/`:** 100 en las cuatro categorías, sin desplazamientos; el LCP (0,65 s) es el título de la página.

## 4. Análisis de refactorización

### R1 — Carga de datos cancelable con estados de carga y error (backoffice)

- **Dónde aparece:** el mismo bloque de unas 25 líneas se repite casi idéntico en **7 hooks**: `useIncidents`, `useIncidentSummary`, `useIngredients`, `useOrders`, `useSuppliers`, `useIngredientStock` y `useIngredientSuppliers`. Variantes del mismo patrón aparecen en `app/(protegido)/talento/page.tsx` y `talento/candidates/[id]/page.tsx`.
  ```ts
  const [state, setState] = useState<{ status: "loading" } | { status: "error"; message } | { status: "success"; … }>(…);
  const [reloadKey, setReloadKey] = useState(0);
  useEffect(() => {
    let cancelled = false;
    async function load() {
      try { const data = await fetcher(); if (!cancelled) setState({ status: "success", data }); }
      catch (err) { if (!cancelled) setState({ status: "error", message: toUserMessage(err, fallback) }); }
    }
    load();
    return () => { cancelled = true; };
  }, [deps, reloadKey]);
  ```
- **Por qué es candidato:**
  - Es lógica, no presentación: el estado de la petición, el descarte de respuestas obsoletas cuando cambian los filtros o se desmonta el componente, y el reintento.
  - Hoy cada copia puede divergir: unas vuelven a `loading` al recargar y otras no, y cada una declara su propio tipo de estado (`FetchState`, `SummaryState`…). `SummaryState` incluso está duplicado entre `useIncidentSummary` y `IncidentSummaryPanel`.
  - Un error en el descarte de respuestas habría que corregirlo 7 veces.
- **Cómo quedaría la abstracción:** un hook genérico en `hooks/useAsyncData.ts`, con un tipo de estado compartido en `types/` que los componentes reutilizan.
  ```ts
  type AsyncState<T> =
    | { status: "loading" }
    | { status: "error"; message: string }
    | { status: "success"; data: T };

  function useAsyncData<T>(
    load: () => Promise<T>,
    deps: React.DependencyList,
    errorMessage: string,
  ): { state: AsyncState<T>; retry: () => void; refresh: () => void };
  ```
  - `retry` vuelve a mostrar la carga (tras un error);
  - `refresh` recarga sin vaciar el bloque (tras un cambio de estado);
  - cada hook de dominio (`useIncidentSummary`, `useIngredients`…) pasa a ser una llamada a `useAsyncData` más su lógica propia, sin cambiar su API pública.

### R2 — Bloque de error con "Reintentar" (backoffice)

- **Dónde aparece:** el mismo marcado (mensaje de error seguido del botón "Reintentar") se repite en **10 archivos**:
  - `components/gestor-incidencias/IncidentPanel.tsx` e `IncidentSummaryPanel.tsx`;
  - `components/incidencias/IncidentAnalysisPanel.tsx`;
  - `components/inventario/IngredientsPanel.tsx` y `OrdersPanel.tsx`;
  - `components/proveedores/SupplierDirectory.tsx`;
  - `components/talento/NotesSection.tsx`;
  - `components/auth/ProtectedShell.tsx`;
  - `app/(protegido)/talento/page.tsx` y `talento/candidates/[id]/page.tsx`.
  ```tsx
  <div role="alert" className="flex flex-col items-start gap-3">
    <ErrorMessage>{message}</ErrorMessage>
    <Button variant="secondary" onClick={onRetry}>Reintentar</Button>
  </div>
  ```
- **Por qué es candidato:**
  - Es la pareja natural de R1: cada bloque que usa el estado de error lo pinta igual.
  - La parte accesible (`role="alert"`) y el texto del botón deben ser coherentes en toda la app, y hoy dependen de copiar bien el fragmento.
- **Cómo quedaría la abstracción:** un componente `components/RetryableError.tsx`.
  ```tsx
  <RetryableError message={state.message} onRetry={retry} compact? />
  ```
  - Reutiliza `ErrorMessage` y `Button`, siguiendo las reglas de UI del proyecto.

### R3 — Logo de la cabecera (website)

- **Dónde aparece:** `components/SiteHeader.tsx` y `components/RegistrationHeader.tsx` declaran el mismo `<Image>` del logo con las mismas 7 props (`src`, `alt`, `width={1245}`, `height={470}`, `sizes="191px"`, `loading="eager"`, `className`).
- **Por qué es candidato:**
  - Es la imagen que aparece en todas las páginas del sitio y su configuración de carga afecta al rendimiento (tamaño servido, prioridad).
  - Si mañana se ajusta (por ejemplo, `fetchPriority` o un SVG), hay que acordarse de cambiarla en dos sitios; y en las dos ya debe coincidir con el `sizes` del CSS (`h-18 w-auto`).
- **Cómo quedaría la abstracción:** `components/BrandLogo.tsx`, sin props obligatorias, que concentra la decisión de carga y el tamaño.
  ```tsx
  <BrandLogo />
  ```
  - Las dos cabeceras lo usan. `RegistrationHeader` lo envuelve en su `Link` a la home, como ahora.

**Qué se extrae en esta auditoría:** R1 y R2 en el backoffice, porque son los de mayor duplicación y riesgo de divergencia, y tocan el gestor de incidencias, la vista corregida en P1. R3, en el website, porque es pequeño y concentra la configuración de la imagen que más pesa en la carga. Los tres van acompañados de pruebas o de su verificación, y no cambian la API pública de los hooks ni el aspecto de las vistas.

## 5. Orden de las correcciones

Una corrección por commit, con nueva medición de la misma URL después de cada una.

1. **P1** — Reservar el espacio del resumen en `/gestor-incidencias` (CLS).
2. **P2** — Quitar `loading="eager"` de la fachada, midiendo el website en móvil y en escritorio (LCP).
3. **P3** — Icono del website (Best Practices).
4. **R1 + R2** — Extraer `useAsyncData` y `RetryableError` en el backoffice.
5. **R3** — Extraer `BrandLogo` en el website.
