import { filterOrders, mergeOrders, NO_ORDER_FILTERS } from "@/lib/inventory-orders";
import type { IngredientEntry, IngredientExit } from "@/types/inventory";

// Proyección plana del ingrediente que acompaña a cada orden (docs/serialization-audit.md, D4).
const INGREDIENT = { ingredient_id: 1, ingredient_name: "Falda de ternera", ingredient_sku: "BRS-BEEF-001", ingredient_unit: "kg" as const };
const USER = "d445afb4-d2f2-4caa-bbf5-9e0023fcfbb2";

function entry(id: number, created_at: string): IngredientEntry {
  return { id, ...INGREDIENT, quantity: 10, location_id: 1, created_at, user_uuid: USER, supplier_name: "Carnes del Valle S.A.S.", unit_cost: 38500 };
}

function exit(id: number, created_at: string): IngredientExit {
  return { id, ...INGREDIENT, quantity: 2, location_id: 1, created_at, user_uuid: USER, reason: "waste", waste_reason: "expired" };
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

describe("filterOrders", () => {
  const plantain = { ingredient_id: 2, ingredient_name: "Plátano maduro", ingredient_sku: "VOL-CO-PRODUCE-003", ingredient_unit: "kg" as const };
  const rows = mergeOrders({
    inbound: [entry(1, "2026-11-14T09:00:00Z"), { ...entry(2, "2026-11-15T09:00:00Z"), ...plantain }],
    outbound: [exit(1, "2026-11-16T12:00:00Z"), { ...exit(2, "2026-11-17T12:00:00Z"), ...plantain }],
  });

  it("sin filtros devuelve todas las órdenes con su recuento por tipo", () => {
    const result = filterOrders(rows, NO_ORDER_FILTERS);
    expect(result.rows).toEqual(rows);
    expect([result.entries, result.exits]).toEqual([2, 2]);
  });

  it("filtra por tipo", () => {
    const result = filterOrders(rows, { kind: "exit", ingredient: "" });
    expect(result.rows.map((row) => row.key)).toEqual(["exit-2", "exit-1"]);
    expect([result.entries, result.exits]).toEqual([0, 2]);
  });

  it("busca el ingrediente sin distinguir mayúsculas ni tildes, y por SKU", () => {
    expect(filterOrders(rows, { kind: "", ingredient: "  PLATANO " }).rows.map((row) => row.key)).toEqual(["exit-2", "entry-2"]);
    expect(filterOrders(rows, { kind: "", ingredient: "brs-beef" }).rows.map((row) => row.key)).toEqual(["exit-1", "entry-1"]);
  });

  it("combina los dos filtros y conserva el orden del historial", () => {
    const result = filterOrders(rows, { kind: "entry", ingredient: "plátano" });
    expect(result.rows.map((row) => row.key)).toEqual(["entry-2"]);
    expect([result.entries, result.exits]).toEqual([1, 0]);
  });

  it("devuelve una lista vacía si nada coincide", () => {
    expect(filterOrders(rows, { kind: "", ingredient: "salmón" })).toEqual({ rows: [], entries: 0, exits: 0 });
  });
});
