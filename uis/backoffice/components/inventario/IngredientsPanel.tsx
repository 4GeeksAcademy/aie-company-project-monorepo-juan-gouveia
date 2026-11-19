"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import EmptyMessage from "@/components/EmptyMessage";
import LoadingMessage from "@/components/LoadingMessage";
import IngredientTable from "@/components/inventario/IngredientTable";
import StockLevelLegend from "@/components/inventario/StockLevelLegend";
import RetryableError from "@/components/RetryableError";
import { useIngredients } from "@/hooks/useIngredients";
import { stockLevel } from "@/lib/inventory-stock-level";
import type { Ingredient } from "@/types/inventory";

// Solo se descarga al pulsar "Ajustar stock", como los demás modales del backoffice.
const StockAdjustModal = dynamic(() => import("@/components/inventario/StockAdjustModal"));

export default function IngredientsPanel() {
  const { ingredients, fetchState, reload } = useIngredients();
  const [adjusting, setAdjusting] = useState<Ingredient | null>(null);

  const levels = ingredients.map((ingredient) => stockLevel(ingredient.current_stock, ingredient.unit));
  const lowCount = levels.filter((level) => level === "low").length;
  const outCount = levels.filter((level) => level === "out").length;

  return (
    <div className="flex flex-col gap-4">
      <StockLevelLegend />

      {fetchState.status === "loading" && <LoadingMessage>Cargando ingredientes...</LoadingMessage>}

      {fetchState.status === "error" && (
        <RetryableError onRetry={reload}>
          {fetchState.message}
        </RetryableError>
      )}

      {fetchState.status === "success" &&
        (ingredients.length === 0 ? (
          <EmptyMessage>Todavía no hay ingredientes registrados.</EmptyMessage>
        ) : (
          <>
            <p className="text-sm text-black" aria-live="polite">
              {ingredients.length} ingredientes: {lowCount} con stock bajo y {outCount} sin stock.
            </p>
            <IngredientTable ingredients={ingredients} onAdjustStock={setAdjusting} />
          </>
        ))}

      {adjusting && <StockAdjustModal ingredient={adjusting} onClose={() => setAdjusting(null)} />}
    </div>
  );
}
