# `@repo/brasa-core`

Modelos de dominio y utilidades de negocio de Brasaland: menú, ventas, locales, desperdicio y métricas por país en USD y COP, con la tasa fija definida en el paquete.

> **Paquete transitorio.** El backend es la fuente de verdad de las reglas de negocio. Este paquete no recibe reglas nuevas ni consumidores nuevos, solo correcciones mientras siga en uso. Sirve de referencia para portar la lógica a Python y se eliminará cuando deje de usarse.

Hoy solo lo usa la herramienta `/funciones` de `uis/backoffice`. Los datos de ejemplo son ilustrativos, no datos reales de la empresa.

## API pública

Todo se exporta desde la raíz del paquete.

| Módulo | Exportaciones |
|---|---|
| `types/models` | `MenuItem`, `Price`, `MenuCategory`, `MenuItemStatus`, `SaleTransaction`, `PaymentMethod`, `Location`, `Country`, `LocationStatus`, `WasteRecord`, `WasteReason`, `CountryMetrics` |
| `utils/collections` | `filterSalesByLocation`, `filterSalesByDateRange`, `filterMenuItemsByCategory`, `filterActiveLocations`, `sortLocationsBySeatingCapacity`, `sortMenuItemsByPrice` |
| `utils/search` | `findLocationById`, `findMenuItemByName`, `binarySearchLocationBySeatingCapacity` |
| `utils/transformations` | `calculateDailyRevenue`, `calculateLocationMargin`, `calculateWasteCost`, `convertCurrency`, `scoreLocationPerformance`, `rankLocationsByPerformance`, `calculateAverageTicket`, `countSalesByPaymentMethod`, `findTopSellingItems`, `groupWasteByReason`, `calculateCountryComparison` |
| `utils/validations` | `validateMenuItem`, `validateSaleTransaction`, `validateLocation`, que devuelven `{ valid, errors[] }` |
| `utils/test-data` | `sampleMenuItems`, `sampleLocations`, `sampleSales`, `sampleWasteRecords`, `invalidMenuItem`, `invalidSale`, `invalidLocation` |

## Cómo se consume

Esta configuración documenta el uso actual en `uis/backoffice`; no debe replicarse en proyectos nuevos. El repositorio no tiene gestor de workspaces y el paquete se distribuye como TypeScript sin compilar:

1. Añade la dependencia en `package.json` y ejecuta `npm install`:

   ```json
   "@repo/brasa-core": "file:../../packages/brasa-core"
   ```

2. Configura `next.config.ts`:

   ```ts
   transpilePackages: ["@repo/brasa-core"],
   turbopack: { root: path.join(__dirname, "../..") },
   ```

3. Importa desde la raíz del paquete:

   ```ts
   import { calculateAverageTicket, sampleSales } from "@repo/brasa-core";
   ```

Los servicios y agentes en Python no pueden importarlo: obtienen estos cálculos a través de la API.

## Estructura

- `index.ts`: punto de entrada público.
- `types/`: modelos de dominio.
- `utils/`: filtros, búsquedas, cálculos, validaciones y datos de ejemplo.

El paquete no tiene scripts propios. Sus tipos se comprueban cuando un consumidor ejecuta `tsc`.

> _Versión en inglés: [README.md](./README.md)._
