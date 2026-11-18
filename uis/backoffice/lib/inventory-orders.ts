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

// Filtros del historial: tipo de orden ("" = todas) y texto que se busca en el nombre o el SKU del
// ingrediente, sin distinguir mayúsculas ni tildes ("platano" encuentra "Plátano maduro").
export interface OrderFilters {
  kind: "" | OrderRow["kind"];
  ingredient: string;
}

export const NO_ORDER_FILTERS: OrderFilters = { kind: "", ingredient: "" };

export interface FilteredOrders {
  rows: OrderRow[];
  entries: number;
  exits: number;
}

function normalize(text: string): string {
  return text.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLocaleLowerCase("es");
}

// Recorre todas las órdenes una vez: con ~21 000 filas cuesta ~5 ms en escritorio y ~30 ms con la
// CPU de un móvil, así que quien lo use debe memoizarlo (OrdersPanel lo hace con useMemo).
export function filterOrders(rows: OrderRow[], { kind, ingredient }: OrderFilters): FilteredOrders {
  const query = normalize(ingredient.trim());
  const result: FilteredOrders = { rows: [], entries: 0, exits: 0 };
  for (const row of rows) {
    if (kind && row.kind !== kind) continue;
    if (query && !normalize(`${row.order.ingredient_name} ${row.order.ingredient_sku}`).includes(query)) continue;
    result.rows.push(row);
    if (row.kind === "entry") result.entries += 1;
    else result.exits += 1;
  }
  return result;
}
