import { useAsyncData } from "@/hooks/useAsyncData";
import { listIngredients } from "@/lib/inventory";

// Carga los ingredientes con su stock actual desde la API. `reload` vuelve a pedirlos (botón
// "Reintentar" tras un error).
export function useIngredients() {
  const { state, reload } = useAsyncData(listIngredients, "No se pudieron cargar los ingredientes.");

  return {
    ingredients: state.status === "success" ? state.data : [],
    fetchState: state,
    reload,
  };
}
