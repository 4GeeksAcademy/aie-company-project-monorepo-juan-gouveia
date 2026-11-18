import Button from "@/components/Button";
import StockLevelBadge from "@/components/inventario/StockLevelBadge";
import type { IngredientStock } from "@/hooks/useIngredientStock";
import { FIELD_LABELS, formatQuantity } from "@/lib/inventory-labels";
import { stockLevel } from "@/lib/inventory-stock-level";

// Stock actual del ingrediente elegido en el formulario de salida, visible antes de escribir la
// cantidad: "Stock actual: 52 kg" con su nivel.
export default function StockPanel({ stock, onRetry }: { stock: IngredientStock; onRetry: () => void }) {
  if (stock.status === "idle") {
    return <p className="text-sm text-gray-600">Elige un ingrediente para ver su stock actual.</p>;
  }
  if (stock.status === "loading") {
    return <p className="text-sm text-gray-600">Cargando el stock actual...</p>;
  }
  if (stock.status === "error") {
    return (
      <div role="alert" className="flex flex-wrap items-center gap-3 text-sm">
        <span className="text-red-700">{stock.message}</span>
        <Button variant="secondary" onClick={onRetry}>
          Reintentar
        </Button>
      </div>
    );
  }
  const { current_stock, unit } = stock.ingredient;
  return (
    <p className="flex flex-wrap items-center gap-2 text-base text-black">
      <span>
        <span className="font-semibold text-red-700">{FIELD_LABELS.current_stock}:</span>{" "}
        <span className="font-semibold">{formatQuantity(current_stock, unit)}</span>
      </span>
      <StockLevelBadge level={stockLevel(current_stock, unit)} />
    </p>
  );
}
