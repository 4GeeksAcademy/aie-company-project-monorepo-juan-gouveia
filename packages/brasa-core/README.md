# `@repo/brasa-core`

Domain models and business utilities for Brasaland: menu, sales, locations, waste, and country metrics in USD and COP, using the fixed rate defined in the package.

It supports the need for centralized data described in `CONTEXT.md`: every consumer applies the same business rules. The sample data is illustrative, not real company data.

## Public API

Everything is exported from the package root.

| Module | Exports |
|---|---|
| `types/models` | `MenuItem`, `Price`, `MenuCategory`, `MenuItemStatus`, `SaleTransaction`, `PaymentMethod`, `Location`, `Country`, `LocationStatus`, `WasteRecord`, `WasteReason`, `CountryMetrics` |
| `utils/collections` | `filterSalesByLocation`, `filterSalesByDateRange`, `filterMenuItemsByCategory`, `filterActiveLocations`, `sortLocationsBySeatingCapacity`, `sortMenuItemsByPrice` |
| `utils/search` | `findLocationById`, `findMenuItemByName`, `binarySearchLocationBySeatingCapacity` |
| `utils/transformations` | `calculateDailyRevenue`, `calculateLocationMargin`, `calculateWasteCost`, `convertCurrency`, `scoreLocationPerformance`, `rankLocationsByPerformance`, `calculateAverageTicket`, `countSalesByPaymentMethod`, `findTopSellingItems`, `groupWasteByReason`, `calculateCountryComparison` |
| `utils/validations` | `validateMenuItem`, `validateSaleTransaction`, `validateLocation`, which return `{ valid, errors[] }` |
| `utils/test-data` | `sampleMenuItems`, `sampleLocations`, `sampleSales`, `sampleWasteRecords`, `invalidMenuItem`, `invalidSale`, `invalidLocation` |

## How to consume it

The repository has no workspace manager, and the package ships uncompiled TypeScript. In a Next.js project:

1. Add the dependency to `package.json` and run `npm install`:

   ```json
   "@repo/brasa-core": "file:../../packages/brasa-core"
   ```

2. Configure `next.config.ts`:

   ```ts
   transpilePackages: ["@repo/brasa-core"],
   turbopack: { root: path.join(__dirname, "../..") },
   ```

3. Import from the package root:

   ```ts
   import { calculateAverageTicket, sampleSales } from "@repo/brasa-core";
   ```

`uis/backoffice` uses it this way. Python services and agents cannot import it directly.

## Structure

- `index.ts`: public entry point.
- `types/`: domain models.
- `utils/`: filters, search, calculations, validations, and sample data.

The package has no scripts of its own. Its types are checked when a consumer runs `tsc`.

> _Spanish version: [README.es.md](./README.es.md)._
