"use client";

import Button from "@/components/Button";
import EmptyMessage from "@/components/EmptyMessage";
import ErrorMessage from "@/components/ErrorMessage";
import LoadingMessage from "@/components/LoadingMessage";
import IngredientTable from "@/components/inventario/IngredientTable";
import StockLevelLegend from "@/components/inventario/StockLevelLegend";
import { useIngredients } from "@/hooks/useIngredients";
import { stockLevel } from "@/lib/inventory-stock-level";

export default function IngredientsPanel() {
  const { ingredients, fetchState, reload } = useIngredients();

  const levels = ingredients.map((ingredient) => stockLevel(ingredient.current_stock, ingredient.unit));
  const lowCount = levels.filter((level) => level === "low").length;
  const outCount = levels.filter((level) => level === "out").length;

  return (
    <div className="flex flex-col gap-4">
      <StockLevelLegend />

      {fetchState.status === "loading" && <LoadingMessage>Cargando ingredientes...</LoadingMessage>}

      {fetchState.status === "error" && (
        <div role="alert" className="flex flex-col items-start gap-3">
          <ErrorMessage>{fetchState.message}</ErrorMessage>
          <Button variant="secondary" onClick={reload}>
            Reintentar
          </Button>
        </div>
      )}

      {fetchState.status === "success" &&
        (ingredients.length === 0 ? (
          <EmptyMessage>Todavía no hay ingredientes registrados.</EmptyMessage>
        ) : (
          <>
            <p className="text-sm text-black" aria-live="polite">
              {ingredients.length} ingredientes: {lowCount} con stock bajo y {outCount} sin stock.
            </p>
            <IngredientTable ingredients={ingredients} />
          </>
        ))}
    </div>
  );
}
