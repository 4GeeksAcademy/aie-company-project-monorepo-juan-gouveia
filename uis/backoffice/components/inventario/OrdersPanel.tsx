"use client";

import Button from "@/components/Button";
import EmptyMessage from "@/components/EmptyMessage";
import ErrorMessage from "@/components/ErrorMessage";
import LoadingMessage from "@/components/LoadingMessage";
import OrderHistory from "@/components/inventario/OrderHistory";
import { useOrders } from "@/hooks/useOrders";
import { useSession } from "@/hooks/useSession";

// Historial de órdenes, solo de lectura.
export default function OrdersPanel() {
  const { orders, fetchState, reload } = useOrders();
  const { user } = useSession();

  const entryCount = orders.filter((row) => row.kind === "entry").length;

  return (
    <div className="flex flex-col gap-4">
      {fetchState.status === "loading" && <LoadingMessage>Cargando el historial...</LoadingMessage>}

      {fetchState.status === "error" && (
        <div role="alert" className="flex flex-col items-start gap-3">
          <ErrorMessage>{fetchState.message}</ErrorMessage>
          <Button variant="secondary" onClick={reload}>
            Reintentar
          </Button>
        </div>
      )}

      {fetchState.status === "success" &&
        (orders.length === 0 ? (
          <EmptyMessage>Todavía no hay órdenes registradas.</EmptyMessage>
        ) : (
          <>
            <p className="text-sm text-black" aria-live="polite">
              {orders.length} órdenes: {entryCount} entradas y {orders.length - entryCount} salidas.
            </p>
            <OrderHistory orders={orders} currentUserId={user?.id ?? null} />
          </>
        ))}
    </div>
  );
}
