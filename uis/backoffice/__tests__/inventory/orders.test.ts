import { mergeOrders } from "@/lib/inventory-orders";
import type { IngredientEntry, IngredientExit } from "@/types/inventory";

// Proyección plana del ingrediente que acompaña a cada orden (docs/serialization-audit.md, D4).
const INGREDIENT = { ingredient_id: 1, ingredient_name: "Falda de ternera", ingredient_sku: "BRS-BEEF-001", ingredient_unit: "kg" as const };
const USER = "d445afb4-d2f2-4caa-bbf5-9e0023fcfbb2";

function entry(id: number, created_at: string): IngredientEntry {
  return { id, ...INGREDIENT, quantity: 10, location_id: 1, created_at, user_uuid: USER, supplier_name: "Carnes del Valle S.A.S." };
}

function exit(id: number, created_at: string): IngredientExit {
  return { id, ...INGREDIENT, quantity: 2, location_id: 1, created_at, user_uuid: USER, reason: "waste" };
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
