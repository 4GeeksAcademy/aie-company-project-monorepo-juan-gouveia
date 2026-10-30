# `@repo/brasa-core`

Modelos de dominio y utilidades de negocio de Brasaland: menú, ventas, locales, desperdicio y métricas por país en USD y COP, con la tasa fija definida en el paquete.

Responde a la necesidad de datos centralizados descrita en `CONTEXT.md`: todos los consumidores aplican las mismas reglas de negocio. Los datos de ejemplo son ilustrativos, no datos reales de la empresa.

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

## Cómo consumirlo

El repositorio no tiene gestor de workspaces y el paquete se distribuye como TypeScript sin compilar. En un proyecto Next.js:

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

`uis/backoffice` lo usa de esta forma. Los servicios y agentes en Python no pueden importarlo directamente.

## Estructura

- `index.ts`: punto de entrada público.
- `types/`: modelos de dominio.
- `utils/`: filtros, búsquedas, cálculos, validaciones y datos de ejemplo.

El paquete no tiene scripts propios. Sus tipos se comprueban cuando un consumidor ejecuta `tsc`.

> _Versión en inglés: [README.md](./README.md)._
