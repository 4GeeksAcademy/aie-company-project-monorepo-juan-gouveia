import type { IngredientEntry, IngredientExit, OrdersResponse } from "@/types/inventory";

// Una fila del historial: la API devuelve las entradas y las salidas en listas separadas, y el
// historial las muestra juntas. `kind` dice de cuál viene cada una.
export type OrderRow =
  | { kind: "entry"; key: string; order: IngredientEntry }
  | { kind: "exit"; key: string; order: IngredientExit };

// Entradas y salidas en una sola lista, de la más reciente a la más antigua. Los ids de entradas y
// salidas son secuencias distintas, así que la clave de React lleva el tipo delante ("entry-5").
// Con la misma fecha, se mantiene el orden de la API (sort es estable).
export function mergeOrders({ inbound, outbound }: OrdersResponse): OrderRow[] {
  const rows: OrderRow[] = [
    ...inbound.map((order) => ({ kind: "entry" as const, key: `entry-${order.id}`, order })),
    ...outbound.map((order) => ({ kind: "exit" as const, key: `exit-${order.id}`, order })),
  ];
  return rows.sort((a, b) => Date.parse(b.order.created_at) - Date.parse(a.order.created_at));
}
