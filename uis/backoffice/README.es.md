# Backoffice de Brasaland

Aplicación interna desde la que el personal de Brasaland accede a sus herramientas en un solo lugar.

Responde a la necesidad de sistemas internos modernos descrita en `CONTEXT.md`. Sus primeras herramientas apoyan la selección de Personas y Cultura y la revisión de la lógica de negocio.

> _Versión en inglés: [README.md](./README.md)._

## Stack

Next.js 16 (App Router), React 19, TypeScript y Tailwind CSS 4. Es un proyecto independiente: no comparte layout con `uis/website`.

## Cómo ejecutarlo

Crea `.env.local` con la URL de la API:

```bash
NEXT_PUBLIC_API_BASE_URL=<url-base-de-la-api>
```

Después ejecuta:

```bash
npm install
npm run dev     # http://localhost:3001
npm run lint
npm run build
```

`npm install` enlaza `@repo/brasa-core` desde `packages/brasa-core`, así que hay que ejecutarlo después de clonar el repositorio.

## Herramientas

| Ruta | Herramienta | Datos |
|---|---|---|
| `/` | Portada con una tarjeta por herramienta | `lib/tools.ts` |
| `/talento` | Talent Pipeline Tracker: candidatos, status, stage y notas | API REST |
| `/funciones` | Pruebas manuales de filtros, búsquedas, reportes y validaciones | Datos de ejemplo de `@repo/brasa-core` |

## Añadir una herramienta

1. Crea su ruta en `app/<herramienta>/`.
2. Pon sus archivos propios en `components/<herramienta>/` y `lib/<herramienta>/`. Las piezas reutilizables van directamente en `components/`.
3. Añade una entrada en `lib/tools.ts`. La portada y la navegación se generan desde esa lista.

## Estructura

- `app/`: layout raíz, portada y una carpeta por herramienta.
- `components/`: componentes base reutilizables, más `talento/` y `funciones/`.
- `hooks/`: hooks personalizados.
- `lib/`: `tools.ts`, `format.ts` y una carpeta por herramienta.
- `types/`: tipos de la API.

## Limitaciones conocidas

- **Sin autenticación:** no debe publicarse hasta que exista el login.
- **Altura de la cabecera:** `FilterBar` depende de su altura fija (57 px en móvil y 89 px desde `md`). En móvil no se muestran los enlaces a herramientas; se navega desde la portada.
- **API compartida:** el tracker usa una API de playground compartida, así que evita escrituras de prueba.
