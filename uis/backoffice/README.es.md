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
```

Las herramientas que usan la API de Brasaland necesitan que esté arrancada; las instrucciones están en [`services/brasaland-api/README.es.md`](../../services/brasaland-api/README.es.md).

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
| `/incidencias` | Análisis de incidencias: sube el CSV de Operaciones, muestra el resumen y los registros inválidos con su motivo, y descarga `results.csv` | API de Brasaland, a través del intermediario |
| `/proveedores` | Directorio de proveedores: listado de activos y suspendidos, filtros por país y categoría, alta, actualización de tarifa y activar o suspender | API de Brasaland (dominio `suppliers`, TinyDB), a través del intermediario |
| `/funciones` | Pruebas manuales de filtros, búsquedas, reportes y validaciones | Datos de ejemplo de `@repo/brasa-core` |

## Añadir una herramienta

1. Crea su ruta en `app/<herramienta>/`.
2. Pon sus archivos propios en `components/<herramienta>/` y `lib/<herramienta>/`. Las piezas reutilizables van directamente en `components/`.
3. Añade una entrada en `lib/tools.ts`. La portada y la navegación se generan desde esa lista.

Las áreas internas, incluida la formación, se incorporan aquí como herramientas, no como aplicaciones aparte. Cuando exista la autenticación, cada entrada de `lib/tools.ts` declarará el permiso que necesita y la lista se filtrará con `GET /auth/me`. Ese filtro solo afecta a la interfaz: la autorización real está en la API.

## Estructura

- `app/`: layout raíz, portada y una carpeta por herramienta.
- `app/api/[...path]/route.ts`: intermediario (BFF) hacia la API de Brasaland. Reenvía `GET`, `POST`, `PATCH` y `DELETE` de `/api/<ruta>` a `API_BASE_URL/<ruta>` sin aplicar lógica, así que la URL de la API se queda en el servidor y no hace falta CORS. Si falta la variable responde 500 (`api_not_configured`); si la API no responde, 502 (`api_unavailable`).
- `components/`: componentes base reutilizables, más `talento/`, `funciones/`, `incidencias/` y `proveedores/`. `FileDropzone` sirve para cualquier herramienta que reciba archivos.
- `hooks/`: hooks personalizados.
- `lib/`: `tools.ts`, `format.ts` y una carpeta por herramienta.
- `types/`: tipos de la API.

## Limitaciones conocidas

- **Sin autenticación:** no debe publicarse hasta que exista el login.
- **`/funciones` es temporal:** prueba las reglas de `@repo/brasa-core`, un paquete transitorio. Cuando esas reglas pasen al backend, debe retirarse o llamar a la API. No añadas cálculos de negocio a los frontends.
- **`/incidencias` descarga el último análisis de la API:** se guarda en memoria, así que si la API se reinicia hay que volver a subir el archivo, y si dos personas analizan a la vez, se descarga el más reciente.
- **`/proveedores` escribe en la base local de la API:** las altas y los cambios de tarifa o estado se guardan en `services/brasaland-api/storage/brasaland-db.json`. Para volver a los datos iniciales, borra ese archivo y reinicia la API. La interfaz no ofrece borrar proveedores: el flujo habitual es suspenderlos.
- **Altura de la cabecera:** `FilterBar` depende de su altura fija (57 px en móvil y 89 px desde `md`). En móvil no se muestran los enlaces a herramientas; se navega desde la portada.
- **API compartida:** el tracker usa una API de playground compartida, así que evita escrituras de prueba.
