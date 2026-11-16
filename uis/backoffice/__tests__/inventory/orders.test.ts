import { mergeOrders } from "@/lib/inventory-orders";
import type { IngredientEntry, IngredientExit } from "@/types/inventory";

const INGREDIENT = { id: 1, name: "Falda de ternera", sku: "BRS-BEEF-001", unit: "kg" as const, country: "CO" as const };
const USER = "d445afb4-d2f2-4caa-bbf5-9e0023fcfbb2";

function entry(id: number, created_at: string): IngredientEntry {
  return { id, ingredient_id: 1, quantity: 10, location_id: 1, created_at, user_uuid: USER, ingredient: INGREDIENT, supplier_name: "Carnes del Valle S.A.S." };
}

function exit(id: number, created_at: string): IngredientExit {
  return { id, ingredient_id: 1, quantity: 2, location_id: 1, created_at, user_uuid: USER, ingredient: INGREDIENT, reason: "waste" };
}

describe("mergeOrders", () => {
  it("junta entradas y salidas de la más reciente a la más antigua", () => {
    const rows = mergeOrders({
      inbound: [entry(2, "2026-11-16T10:00:00Z"), entry(1, "2026-11-14T09:00:00Z")],
      outbound: [exit(1, "2026-11-15T12:00:00Z")],
    });
    expect(rows.map((row) => row.key)).toEqual(["entry-2", "exit-1", "entry-1"]);
    expect(rows.map((row) => row.kind)).toEqual(["entry", "exit", "entry"]);
  });

  it("da claves distintas a una entrada y una salida con el mismo id", () => {
    const rows = mergeOrders({ inbound: [entry(1, "2026-11-14T09:00:00Z")], outbound: [exit(1, "2026-11-14T09:00:00Z")] });
    expect(new Set(rows.map((row) => row.key)).size).toBe(2);
  });

  it("devuelve una lista vacía si no hay órdenes", () => {
    expect(mergeOrders({ inbound: [], outbound: [] })).toEqual([]);
  });
});
