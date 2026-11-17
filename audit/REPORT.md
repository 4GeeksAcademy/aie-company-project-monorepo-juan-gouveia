# Informe de mejoras — website y backoffice

Correcciones y refactorizaciones aplicadas tras la auditoría de rendimiento ([`AUDIT.md`](AUDIT.md)), su impacto medido sobre las puntuaciones iniciales y la valoración de qué funcionó. El ciclo completo fue: **medir** ([`before/`](before/)) → **analizar** (`AUDIT.md`) → **corregir** (un problema por commit) → **volver a medir** ([`after/`](after/)).

## 1. Resumen

| Frontend | Mejora medida | Corrección |
|---|---|---|
| Backoffice | `/gestor-incidencias`: **CLS 0,065 (hasta 0,204) → 0** y **Performance 99 (90–99) → 100** en todas las ejecuciones | P1: espacio reservado para el resumen |
| Website | **Best Practices 96 → 100** en las 4 mediciones (`/` y `/registro`, escritorio y móvil) | P3: icono del sitio |

- Además se extrajeron **tres abstracciones compartidas** (un hook y dos componentes) sin cambiar el comportamiento ni el HTML de las vistas.
- Una hipótesis (P2, LCP en móvil) **se midió y se descartó**, y el cambio se revirtió (sección 3.2).

## 2. Condiciones de la comparación

Las mismas en el "antes" y el "después" (detalle en [`AUDIT.md` §1](AUDIT.md#1-método)):

- **Modo y versión:** producción (`build` + `start`) fuera de Docker, Chrome 157 y Lighthouse 13.5.0 en DevTools y en el CLI.
- **Perfiles:** móvil (Moto G Power emulado, 4G lenta, CPU ×4) y escritorio (preset `desktop`), con caché fría.
- **Backoffice:** con la sesión iniciada.
- **Cifras:** mediana por métrica de **3 ejecuciones** del CLI; el rango aparece entre paréntesis cuando las ejecuciones no coinciden.
- **Evidencia:** las capturas de DevTools están en `before/` y `after/`, junto al JSON de cada medición.

Cada corrección se midió además por separado, en la misma URL y justo después del cambio (sección 3).

## 3. Correcciones aplicadas

### 3.1 P1 — Reservar el espacio del resumen en el gestor de incidencias (backoffice)

- **Commit:** `48b27eb`.
- **Archivo:** `uis/backoffice/components/gestor-incidencias/IncidentSummaryPanel.tsx`.
- **Skill:** `core-web-vitals` → `references/CLS.md`, *Handle dynamic content deliberately*: "allocate a stable container before the content arrives".
- **Problema:** mientras cargaba, el resumen ocupaba una línea; al llegar los datos crecía unos 600 px y empujaba el listado hacia abajo. El CLS dependía de qué petición respondiera antes (0,065–0,204).
- **Cambio:**
  - mientras carga, el resumen pinta ya su cuadrícula final (5 tarjetas y 3 desgloses) con las etiquetas reales y "—" en lugar de cada cifra;
  - se puede hacer de forma exacta porque los estados, categorías, orígenes y sedes son fijos (`lib/gestor-incidencias/labels.ts`);
  - el aviso de carga se mantiene para lectores de pantalla (`sr-only` y `aria-busy`).
- **Medición** (escritorio, 5 ejecuciones porque el problema era intermitente):

| | Performance | CLS | Desplazamientos detectados |
|---|---|---|---|
| Antes | 99 (90–99) | 0,065 (0,065–0,204) | La sección del listado |
| Después | **100** (100–100) | **0** (0 en las 5) | Ninguno |

### 3.2 P2 — Fachada sin `loading="eager"` (website): hipótesis descartada

- **Sin commit:** el cambio se revirtió tras medirlo.
- **Skills:**
  - `performance` → *LCP image priority*: "Below-fold images: lazy loading";
  - `core-web-vitals` → `references/LCP.md`.
- **Hipótesis:** la foto de la fachada (`History.tsx`) usa `loading="eager"`. Es el LCP en escritorio, pero en móvil queda bajo el pliegue y compite por la red con el CSS y el JS del primer pintado. Con carga diferida, el LCP simulado en móvil (2,54 s) debería bajar del umbral de 2,5 s.
- **Medición** (5 ejecuciones por modo):

| | Antes | Sin `eager` |
|---|---|---|
| Móvil: LCP | 2,54 s (2,46–2,55) | 2,55 s (2,47–2,59) |
| Móvil: Performance | 97 | 97 |
| Escritorio: espera antes de pedir la imagen LCP | 8 ms | 68 ms |
| Escritorio: "LCP resources should not use loading=lazy" | Cumple | **Falla** |

- **Por qué no funcionó:**
  - Chrome pide las imágenes diferidas en cuanto están a cierta distancia del viewport. En una página tan corta, la fachada y las 3 fotos de "¿Qué nos hace únicos?" entran en ese margen.
  - La fachada solo pasó de pedirse a los 17 ms a los 90 ms, que sigue siendo antes del LCP observado (~200 ms), así que la simulación la cuenta igual.
  - En escritorio, donde la fachada es la imagen LCP, el cambio empeoraba el descubrimiento.
- **Decisión:** revertir. Mantenerlo habría sido un cambio sin mejora medida que además hacía fallar una auditoría.
- **Conclusión:** la mayor parte de la estimación viene del JavaScript del framework. `/registro` no tiene esas imágenes y aun así marca 2,2 s; es P5, que no se corrige sin cambiar la compilación. El LCP **observado** de la home es el primer pintado (~0,2 s).

### 3.3 P3 — Icono del sitio (website)

- **Commit:** `5c2f412`.
- **Archivo:** `uis/website/app/icon.tsx` (nuevo).
- **Problema:** el website no declaraba ningún icono. El navegador pedía `/favicon.ico` y recibía un 404 que quedaba como error en la consola (`errors-in-console`), la única auditoría que fallaba en Best Practices.
- **Cambio:**
  - icono generado con `ImageResponse` de `next/og`, según la convención `app/icon` de Next 16 consultada en `node_modules/next/dist/docs`: una "B" blanca sobre el rojo de la marca;
  - se genera en el build como PNG estático, y Next añade el `<link rel="icon">` en todas las páginas;
  - no había un icono oficial, así que el diseño lo eligió el desarrollador.
- **Medición:** Best Practices **96 → 100** en `/` y `/registro`, en escritorio y móvil. La petición del icono responde 200.

### 3.4 Problemas que no se corrigieron, con motivo

| ID | Problema | Motivo |
|---|---|---|
| P4 | El CSS (5 KB) bloquea el render (~155 ms simulados en móvil) | La alternativa, incrustar el CSS (`experimental.inlineCss`), es experimental y cambia cómo sirve el CSS toda la app. Eso es arquitectura, no una corrección dirigida, y la hoja ya está muy por debajo de los 14 KB de CSS crítico que propone la skill. |
| P5 | JS del framework: ~14 KB de polyfills y ~49 KB sin usar | Es el runtime de Next.js y React, no código propio. Reducirlo exige tocar la configuración de compilación o los navegadores objetivo. Es la causa dominante del LCP simulado en móvil (ver 3.2). |

## 4. Refactorizaciones

| ID | Abstracción | Commit | Dónde se integró | Verificación |
|---|---|---|---|---|
| R1 | Hook `hooks/useAsyncData.ts` + tipo `AsyncState<T>` (backoffice) | `8ed12c2` | `useIncidentSummary`, `useIncidents`, `useIngredients`, `useOrders` y `useSuppliers`; el tipo sustituye a 3 tipos de estado duplicados | 7 pruebas nuevas del hook (Jest + `react-dom`), 170/170; prueba de humo de las 4 vistas y del filtro del gestor |
| R2 | Componente `components/RetryableError.tsx` (backoffice) | `448ee2b` | 8 archivos: gestor (resumen y listado), ingredientes, órdenes, proveedores, notas y las dos páginas del tracker | Estado de error forzado con un 503 simulado en el navegador: aparecen los dos avisos y "Reintentar" recupera los datos |
| R3 | Componente `components/BrandLogo.tsx` (website) | `ae6eb10` | `SiteHeader` y `RegistrationHeader` | El HTML del logo es idéntico byte a byte en `/` y `/registro` antes y después |

- **R1:** elimina unas 170 líneas duplicadas.
  - Concentra el descarte de respuestas obsoletas, que antes estaba copiado en cada hook.
  - Los hooks que filtran pasan su función de carga memorizada con `useCallback`, así el lint comprueba sus dependencias sin `eslint-disable`.
  - No se migraron `useIngredientStock` y `useIngredientSuppliers`: atan el estado al id del ingrediente y tienen un estado `idle`.
- **R2:** la parte accesible (`role="alert"`) queda en un solo sitio. Los dos bloques que no se migraron (`ProtectedShell` e `IncidentAnalysisPanel`) son variantes distintas, no copias.
- **R3:** documenta y concentra la configuración de carga de la imagen que aparece en todas las páginas.

Ninguna refactorización cambia la API pública de los hooks ni el aspecto de las vistas. La única diferencia visual es el espacio entre el mensaje y el botón en las notas de candidatos, que pasa de 8 a 12 px, igual que en el resto.

## 5. Comparativa antes / después

Mediana por métrica de 3 ejecuciones; en negrita, lo que cambia.

### Puntuaciones

| Página | Modo | Performance | Accessibility | Best Practices | SEO |
|---|---|---|---|---|---|
| website `/` | escritorio | 100 → 100 | 100 → 100 | **96 → 100** | 100 → 100 |
| website `/` | móvil | 97 → 97 | 100 → 100 | **96 → 100** | 100 → 100 |
| website `/registro` | escritorio | 100 → 100 | 100 → 100 | **96 → 100** | 100 → 100 |
| website `/registro` | móvil | **99 → 98** ¹ | 100 → 100 | **96 → 100** | 100 → 100 |
| backoffice `/` | escritorio | 100 → 100 | 100 → 100 | 100 → 100 | 100 → 100 |
| backoffice `/gestor-incidencias` | escritorio | **99 (90–99) → 100** | 100 → 100 | 100 → 100 | 100 → 100 ² |

### Métricas

| Página | Modo | FCP | LCP | TBT | CLS | Speed Index |
|---|---|---|---|---|---|---|
| website `/` | escritorio | 0,21 → 0,21 s | 0,54 → 0,54 s | 0 → 0 ms | 0 → 0 | 0,23 → 0,24 s |
| website `/` | móvil | 0,76 → 0,76 s | 2,54 → 2,53 s | 46 → 38 ms | 0 → 0 | 0,76 → 0,76 s |
| website `/registro` | escritorio | 0,21 → 0,21 s | 0,48 → 0,48 s | 0 → 0 ms | 0 → 0 | 0,21 → 0,21 s |
| website `/registro` | móvil | 0,76 → 0,76 s | 2,21 → 2,25 s | **30 → 91 ms** ¹ | 0 → 0 | 0,76 → 0,76 s |
| backoffice `/` | escritorio | 0,21 → 0,21 s | 0,65 → 0,59 s | 0 → 0 ms | 0 → 0 | 0,21 → 0,21 s |
| backoffice `/gestor-incidencias` | escritorio | 0,21 → 0,21 s | 0,69 → 0,69 s | 0 → 0 ms | **0,065 (hasta 0,204) → 0** | 0,21 → 0,21 s |

¹ **TBT de `/registro` en móvil.** Se investigó con una prueba A/B alternada, 4 rondas: la versión inicial (`a499311`), compilada en un worktree temporal, frente a la final, en la misma máquina y en el mismo momento.

- **TBT:** base 33–41 ms, final 55–82 ms. La diferencia es consistente, pero **no hay más trabajo en el hilo principal**: el chunk del framework, idéntico, ocupa 182–194 ms de ejecución en las dos versiones.
- **Lo que cambia es la red:** la base pide `/favicon.ico` y recibe un 404; la final pide `/icon` y recibe un PNG. Con ese grafo distinto, la simulación de Lighthouse (Lantern) coloca la tarea de hidratación unos 150 ms antes (2107 frente a 2258 ms), y la misma tarea larga cae de otra forma dentro de la ventana en la que se calcula el TBT.
- **Impacto:** se queda lejos del umbral de 200 ms; Performance da 98–99 en ambas versiones.

² **SEO del gestor.** En la primera tanda de la medición final, una de las 3 ejecuciones dio SEO 92: Lighthouse no logró descargar `robots.txt` ("Timed out fetching resource"), aunque responde 404 en ~2 ms y con un 404 esa auditoría pasa. Se repitió la medición y dio 100 en las 3 ejecuciones.

## 6. Valoración: qué tuvo mayor impacto

1. **P1 (CLS del gestor)** es la corrección de mayor impacto real.
   - Era el único Core Web Vital que llegaba a "necesita mejorar" (0,204), y lo sufría quien usa a diario la vista más cargada del backoffice: el listado saltaba ~600 px justo cuando se iba a pulsar un filtro o un estado.
   - Era intermitente, así que una sola medición podía no verlo; las 3 ejecuciones lo destaparon. Ahora es 0 en todas, y el peor caso de Performance pasa de 90 a 100.
   - Cuesta poco y sigue el patrón que la skill recomienda (contenedor estable antes de los datos).
2. **P3 (icono)** es el mayor cambio de puntuación en el website (+4 en Best Practices en las 4 mediciones) y quita una petición fallida en cada visita. Su efecto en el rendimiento es nulo; su valor está en la calidad y en la apariencia del sitio en pestañas y buscadores.
3. **P2 (descartada)** dejó la lección más útil del ciclo: el LCP de Lighthouse en móvil es una **estimación** que depende de la versión de la herramienta.
   - Con 13.6.0 salía 0,76 s y con 13.5.0, 2,54 s, sobre el mismo código. El LCP observado es ~0,2 s.
   - Medir antes de dar por buena una corrección evitó publicar un cambio que no mejoraba nada y empeoraba el escritorio.
4. **Las refactorizaciones (R1–R3)** no mueven las puntuaciones, ni debían hacerlo. Reducen el código duplicado y el riesgo de divergencia en las piezas que tocan las correcciones: el gestor de incidencias y el logo de todas las páginas. Además, R1 deja probado con pruebas el descarte de respuestas obsoletas.

## 7. Evidencia de uso de las skills

- **Instalación:** `core-web-vitals` y `performance` (`addyosmani/web-quality-skills@afa8da9`) se leyeron completas antes de instalarlas en el proyecto (sin commit). El agente las cargó al corregir P1 (`core-web-vitals`) y P2 (`performance`).
- **Método** (`performance/references/MEASUREMENT.md`): versión de Lighthouse compatible con la de DevTools, JSON guardados, mediana de 3 con rango, condiciones registradas, y separación entre métricas medidas e hipótesis del código.
- **Clasificación de los hallazgos** (`AUDIT.md` §1): requerido si hay una métrica o auditoría que falla con causa demostrada; sugerencia si sale del checklist sin medición que lo respalde.
- **Correcciones:**
  - P1 sigue `CLS.md` (contenedor estable);
  - P2 se planteó con `LCP.md` y la sección *LCP image priority*, y se descartó con la regla de las skills: "re-run equivalent lab measurements and report before/after values".

## 8. Pendiente y recomendaciones

- **Datos de campo:** no hay CrUX para `localhost` ni RUM. En producción convendría medir LCP, INP y CLS reales con la librería `web-vitals` (`performance/references/RUM.md`) antes de priorizar nuevas optimizaciones.
- **JS del framework (P5):** la vía para el LCP simulado en móvil es reducir el runtime cargado antes del primer pintado. Es una decisión de arquitectura y compilación, no de esta auditoría.
- **Actualizar Next a 16.4.6 (parche de seguridad pendiente):** quedó fuera para no contaminar la comparación. Al aplicarlo, conviene repetir estas mediciones con la misma versión de Lighthouse.
- **Extender R1 y R2:** quedan sin migrar las páginas del tracker (`talento`), que siguen una variante del patrón de carga, y los hooks ligados a un id. Se pueden migrar si el patrón se repite más.

## 9. Criterios de evaluación

| Criterio | Dónde se cumple |
|---|---|
| Lighthouse antes y después en modo producción, con capturas en el repositorio | `before/` y `after/`: 6 capturas y JSON por fase; `build` + `start`, nunca `next dev` |
| `AUDIT.md` identifica problemas concretos con su causa raíz | `AUDIT.md` §3: evidencia, causa, skill y clasificación de cada problema |
| Al menos un componente reutilizable o Custom Hook extraído e integrado | R1 (`useAsyncData`), R2 (`RetryableError`) y R3 (`BrandLogo`), sección 4 |
| `REPORT.md` muestra una mejora medible en al menos una puntuación por frontend | Website: Best Practices 96 → 100; backoffice: Performance 99 (90–99) → 100 y CLS → 0 (secciones 1 y 5) |
| Evidencia de uso de las skills instaladas | Sección 7 y la referencia de skill en cada problema de `AUDIT.md` |
| Correcciones que atacan causas reales | P1 reserva el espacio del contenido dinámico; P3 añade el recurso que faltaba; P2 se revirtió al no mostrar mejora |
| Calidad del código sin regresiones | 170/170 pruebas, `tsc` y `eslint` limpios, builds de producción, pruebas de humo y de error en el navegador; el único cambio de métrica (TBT de `/registro`) está explicado en la nota ¹ |
