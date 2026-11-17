import { useAsyncData } from "@/hooks/useAsyncData";
import { listOrders } from "@/lib/inventory";
import { mergeOrders } from "@/lib/inventory-orders";

// Fuera del hook para que useAsyncData reciba siempre la misma función y no repita la petición.
const loadOrders = async () => mergeOrders(await listOrders());

// Carga el historial de órdenes (entradas y salidas juntas, de la más reciente a la más antigua).
// `reload` vuelve a pedirlo (botón "Reintentar" tras un error).
export function useOrders() {
  const { state, reload } = useAsyncData(loadOrders, "No se pudo cargar el historial de órdenes.");

  return {
    orders: state.status === "success" ? state.data : [],
    fetchState: state,
    reload,
  };
}
