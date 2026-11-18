import StockLevelBadge from "@/components/inventario/StockLevelBadge";
import { LOW_STOCK_THRESHOLDS } from "@/lib/inventory-stock-level";
import type { Unit } from "@/types/inventory";

// Los umbrales se leen de LOW_STOCK_THRESHOLDS: si Operaciones los ajusta, la leyenda cambia sola.
const thresholds = (Object.entries(LOW_STOCK_THRESHOLDS) as [Unit, number][])
  .map(([unit, threshold]) => `${threshold} ${unit}`)
  .join(", ");

export default function StockLevelLegend() {
  return (
    <section aria-labelledby="stock-legend-title" className="rounded-lg border border-red-200 bg-white p-4 text-sm">
      <h2 id="stock-legend-title" className="mb-2 font-semibold text-red-700">
        Niveles de stock
      </h2>
      <ul className="flex flex-col gap-2">
        <li className="flex flex-wrap items-center gap-2">
          <StockLevelBadge level="out" />
          <span className="text-black">el stock actual es 0: no se puede registrar ninguna salida.</span>
        </li>
        <li className="flex flex-wrap items-center gap-2">
          <StockLevelBadge level="low" />
          <span className="text-black">por debajo del umbral de su unidad ({thresholds}).</span>
        </li>
        <li className="flex flex-wrap items-center gap-2">
          <StockLevelBadge level="healthy" />
          <span className="text-black">igual o por encima de ese umbral.</span>
        </li>
      </ul>
    </section>
  );
}
