import { useEffect, useState } from "react";
import { getIngredient } from "@/lib/inventory";
import { toUserMessage } from "@/lib/error-message";
import type { Ingredient } from "@/types/inventory";

// Cada estado recuerda de qué ingrediente es: así nunca se muestra el stock de uno anterior.
type StockState =
  | { id: string; status: "loading" }
  | { id: string; status: "error"; message: string }
  | { id: string; status: "success"; ingredient: Ingredient };

export type IngredientStock = { status: "idle" } | StockState;

// Stock actual del ingrediente elegido en el formulario de salida. Se pide a la API (GET
// /inventory/products/{id}) cada vez que cambia el ingrediente y cuando se llama a `refresh`
// (tras registrar una salida o recibir un 400 de stock insuficiente). Si el usuario cambia de
// ingrediente antes de que llegue la respuesta, la anterior se descarta.
export function useIngredientStock(ingredientId: string) {
  const [state, setState] = useState<StockState | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    if (!ingredientId) return;
    let cancelled = false;

    async function load() {
      setState({ id: ingredientId, status: "loading" });
      try {
        const ingredient = await getIngredient(Number(ingredientId));
        if (cancelled) return;
        setState({ id: ingredientId, status: "success", ingredient });
      } catch (err) {
        if (cancelled) return;
        setState({
          id: ingredientId,
          status: "error",
          message: toUserMessage(err, "No se pudo cargar el stock del ingrediente."),
        });
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [ingredientId, refreshKey]);

  // Sin ingrediente no hay nada que mostrar; con un estado de otro ingrediente, se está cargando.
  let stock: IngredientStock;
  if (!ingredientId) stock = { status: "idle" };
  else if (!state || state.id !== ingredientId) stock = { id: ingredientId, status: "loading" };
  else stock = state;

  return { stock, refresh: () => setRefreshKey((key) => key + 1) };
}
