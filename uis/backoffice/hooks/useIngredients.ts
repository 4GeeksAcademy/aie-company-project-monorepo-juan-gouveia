import { useEffect, useState } from "react";
import { listIngredients } from "@/lib/inventory";
import { toUserMessage } from "@/lib/error-message";
import type { Ingredient } from "@/types/inventory";

type FetchState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "success" };

// Carga los ingredientes con su stock actual desde la API. `reload` vuelve a pedirlos (botón
// "Reintentar" tras un error).
export function useIngredients() {
  const [ingredients, setIngredients] = useState<Ingredient[]>([]);
  const [fetchState, setFetchState] = useState<FetchState>({ status: "loading" });
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    // Si el componente se desmonta o se recarga antes de que llegue la respuesta, se descarta.
    let cancelled = false;

    async function load() {
      setFetchState({ status: "loading" });
      try {
        const data = await listIngredients();
        if (cancelled) return;
        setIngredients(data);
        setFetchState({ status: "success" });
      } catch (err) {
        if (cancelled) return;
        setFetchState({
          status: "error",
          message: toUserMessage(err, "No se pudieron cargar los ingredientes."),
        });
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  return {
    ingredients,
    fetchState,
    reload: () => setReloadKey((key) => key + 1),
  };
}
