// Niveles de stock del inventario (lib/inventory-stock-level.ts, decisión F4): sin stock, bajo o
// saludable, con un umbral por unidad.
import { LOW_STOCK_THRESHOLDS, STOCK_LEVEL_LABELS, stockLevel } from "@/lib/inventory-stock-level";

describe("stockLevel", () => {
  it("0 es sin stock en cualquier unidad", () => {
    expect([stockLevel(0, "kg"), stockLevel(0, "litro"), stockLevel(0, "unidad")]).toEqual(["out", "out", "out"]);
  });

  it.each([
    ["kg", 39.9, 40],
    ["litro", 24.5, 25],
    ["unidad", 99, 100],
  ] as const)("en %s, por debajo del umbral es bajo y en el umbral es saludable", (unit, below, threshold) => {
    expect(LOW_STOCK_THRESHOLDS[unit]).toBe(threshold);
    expect(stockLevel(below, unit)).toBe("low");
    expect(stockLevel(threshold, unit)).toBe("healthy");
  });

  it("una cantidad mínima por encima de 0 ya no es sin stock", () => {
    expect(stockLevel(0.1, "kg")).toBe("low");
  });

  it("con la semilla del briefing se ven los tres niveles", () => {
    expect(stockLevel(52, "kg")).toBe("healthy"); // Falda de ternera
    expect(stockLevel(32, "kg")).toBe("low"); // Costilla de cerdo
    expect(stockLevel(20, "litro")).toBe("low"); // Chimichurri
    expect(stockLevel(0, "unidad")).toBe("out"); // Caja para llevar (M)
  });

  it("cada nivel tiene su texto, no solo un color", () => {
    expect(STOCK_LEVEL_LABELS).toEqual({ out: "Sin stock", low: "Stock bajo", healthy: "Stock saludable" });
  });
});
