import { useEffect, useState } from "react";
import { listOrders } from "@/lib/inventory";
import { mergeOrders, type OrderRow } from "@/lib/inventory-orders";
import { toUserMessage } from "@/lib/error-message";

type FetchState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "success" };

// Carga el historial de órdenes (entradas y salidas juntas, de la más reciente a la más antigua).
// `reload` vuelve a pedirlo (botón "Reintentar" tras un error).
export function useOrders() {
  const [orders, setOrders] = useState<OrderRow[]>([]);
  const [fetchState, setFetchState] = useState<FetchState>({ status: "loading" });
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    // Si el componente se desmonta o se recarga antes de que llegue la respuesta, se descarta.
    let cancelled = false;

    async function load() {
      setFetchState({ status: "loading" });
      try {
        const data = await listOrders();
        if (cancelled) return;
        setOrders(mergeOrders(data));
        setFetchState({ status: "success" });
      } catch (err) {
        if (cancelled) return;
        setFetchState({
          status: "error",
          message: toUserMessage(err, "No se pudo cargar el historial de órdenes."),
        });
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  return {
    orders,
    fetchState,
    reload: () => setReloadKey((key) => key + 1),
  };
}
