import Link from "next/link";
import StockLevelBadge from "@/components/inventario/StockLevelBadge";
import { COUNTRY_DESCRIPTIONS, FIELD_LABELS, formatQuantity } from "@/lib/inventory-labels";
import { stockLevel } from "@/lib/inventory-stock-level";
import type { Ingredient } from "@/types/inventory";

// Una sola lista: tarjetas apiladas en móvil y tablet, y columnas alineadas desde lg (con siete
// columnas, md se queda estrecho).
const COLUMNS =
  "lg:grid lg:grid-cols-[minmax(0,2fr)_minmax(0,1.2fr)_6rem_minmax(0,1.2fr)_5rem_minmax(0,1.4fr)_9rem] lg:items-center lg:gap-4";

const ACTION_LINK =
  "rounded-md border border-red-200 px-3 py-1.5 text-center text-xs font-semibold text-red-700 hover:bg-red-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700";

// Etiqueta de campo visible solo en las tarjetas (en lg la da la cabecera de columnas).
function CardLabel({ children }: { children: React.ReactNode }) {
  return <span className="font-semibold text-red-700 lg:hidden">{children}: </span>;
}

interface IngredientTableProps {
  ingredients: Ingredient[];
  // "Ajustar stock": abre el modal que intenta el cambio directo (lo rechaza la API).
  onAdjustStock: (ingredient: Ingredient) => void;
}

export default function IngredientTable({ ingredients, onAdjustStock }: IngredientTableProps) {
  return (
    <div className="rounded-lg border border-red-200 bg-white shadow-md">
      <div
        aria-hidden="true"
        className={`hidden border-b border-red-200 px-4 py-2 text-xs font-semibold uppercase text-red-700 ${COLUMNS}`}
      >
        <span>{FIELD_LABELS.name}</span>
        <span>{FIELD_LABELS.sku}</span>
        <span>{FIELD_LABELS.category}</span>
        <span>{FIELD_LABELS.country}</span>
        <span>{FIELD_LABELS.unit}</span>
        <span>{FIELD_LABELS.current_stock}</span>
        <span>Órdenes</span>
      </div>

      <ul className="divide-y divide-red-100">
        {ingredients.map((ingredient) => {
          const query = `?ingredient_id=${ingredient.id}`;
          return (
            <li key={ingredient.id} className={`flex flex-col gap-2 px-4 py-4 ${COLUMNS}`}>
              <p className="font-semibold text-black">{ingredient.name}</p>

              <p className="break-all text-sm text-black">
                <CardLabel>{FIELD_LABELS.sku}</CardLabel>
                {ingredient.sku}
              </p>

              <p className="text-sm text-black">
                <CardLabel>{FIELD_LABELS.category}</CardLabel>
                {ingredient.category}
              </p>

              <p className="text-sm text-black">
                <CardLabel>{FIELD_LABELS.country}</CardLabel>
                {ingredient.country} ({COUNTRY_DESCRIPTIONS[ingredient.country]})
              </p>

              <p className="text-sm text-black">
                <CardLabel>{FIELD_LABELS.unit}</CardLabel>
                {ingredient.unit}
              </p>

              <div className="flex flex-wrap items-center gap-2 text-sm text-black lg:flex-col lg:items-start lg:gap-1">
                <span>
                  <CardLabel>{FIELD_LABELS.current_stock}</CardLabel>
                  <span className="font-semibold">{formatQuantity(ingredient.current_stock, ingredient.unit)}</span>
                </span>
                <StockLevelBadge level={stockLevel(ingredient.current_stock, ingredient.unit)} />
              </div>

              <div className="mt-1 flex flex-wrap gap-2 lg:mt-0 lg:flex-col">
                <Link
                  href={`/inventario/ordenes/entrada${query}`}
                  aria-label={`Registrar entrada de ${ingredient.name}`}
                  className={ACTION_LINK}
                >
                  Registrar entrada
                </Link>
                <Link
                  href={`/inventario/ordenes/salida${query}`}
                  aria-label={`Registrar salida de ${ingredient.name}`}
                  className={ACTION_LINK}
                >
                  Registrar salida
                </Link>
                <button
                  type="button"
                  onClick={() => onAdjustStock(ingredient)}
                  aria-label={`Ajustar stock de ${ingredient.name}`}
                  className={ACTION_LINK}
                >
                  Ajustar stock
                </button>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
