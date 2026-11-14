// Validación en el cliente de los formularios de entrada y salida (lib/inventory-validation.ts) y
// las utilidades de etiquetas del inventario (lib/inventory-labels.ts).
import { formatAmount, formatQuantity, LOCATION_OPTIONS, locationLabel } from "@/lib/inventory-labels";
import {
  EMPTY_ENTRY_FORM,
  EMPTY_EXIT_FORM,
  exceedsStock,
  parseQuantity,
  toEntryInput,
  toExitInput,
  validateEntryForm,
  validateExitForm,
} from "@/lib/inventory-validation";

const VALID_ENTRY = { ingredient_id: "1", quantity: "50", supplier_name: "  Carnes del Valle S.A. ", location_id: "1" };
const VALID_EXIT = { ingredient_id: "1", quantity: "3,5", reason: "waste" as const, location_id: "14" };

describe("parseQuantity", () => {
  it.each([
    ["12", 12],
    ["12.5", 12.5],
    ["12,5", 12.5],
    [" 0.25 ", 0.25],
    [".5", 0.5],
  ])("lee %p como %p", (text, expected) => {
    expect(parseQuantity(text)).toBe(expected);
  });

  it.each(["", "abc", "-3", "1e3", "12.", "1.2.3"])("%p no es una cantidad", (text) => {
    expect(parseQuantity(text)).toBeNull();
  });
});

describe("validateEntryForm", () => {
  it("un formulario completo no tiene errores", () => {
    expect(validateEntryForm(VALID_ENTRY)).toEqual({});
  });

  it("vacío marca los cuatro campos", () => {
    expect(Object.keys(validateEntryForm(EMPTY_ENTRY_FORM)).sort()).toEqual(
      ["ingredient_id", "location_id", "quantity", "supplier_name"].sort()
    );
  });

  it.each([
    [{ quantity: "0" }, "quantity", "La cantidad debe ser mayor que 0."],
    [{ quantity: "doce" }, "quantity", "Escribe un número, por ejemplo 12 o 12.5."],
    [{ supplier_name: "   " }, "supplier_name", "Escribe el nombre del proveedor."],
    [{ supplier_name: "x".repeat(121) }, "supplier_name", "El proveedor no puede superar 120 caracteres."],
    [{ location_id: "15" }, "location_id", "Elige el local."],
  ])("con %p marca %s", (changes, field, message) => {
    expect(validateEntryForm({ ...VALID_ENTRY, ...changes })).toEqual({ [field]: message });
  });

  it("toEntryInput convierte los textos al cuerpo de la API", () => {
    expect(toEntryInput(VALID_ENTRY)).toEqual({
      ingredient_id: 1,
      quantity: 50,
      supplier_name: "Carnes del Valle S.A.",
      location_id: 1,
    });
  });
});

describe("validateExitForm", () => {
  it("un formulario completo no tiene errores", () => {
    expect(validateExitForm(VALID_EXIT)).toEqual({});
  });

  it("vacío marca ingrediente, cantidad, motivo y local", () => {
    expect(Object.keys(validateExitForm(EMPTY_EXIT_FORM)).sort()).toEqual(
      ["ingredient_id", "location_id", "quantity", "reason"].sort()
    );
  });

  it("toExitInput admite la coma decimal", () => {
    expect(toExitInput(VALID_EXIT)).toEqual({ ingredient_id: 1, quantity: 3.5, reason: "waste", location_id: 14 });
  });
});

describe("exceedsStock", () => {
  it("avisa solo si la cantidad supera el stock mostrado", () => {
    expect(exceedsStock("60", 52)).toBe(true);
    expect(exceedsStock("52", 52)).toBe(false);
    expect(exceedsStock("0,5", 0)).toBe(true);
  });

  it("sin cantidad válida o sin stock cargado no avisa", () => {
    expect(exceedsStock("", 52)).toBe(false);
    expect(exceedsStock("abc", 52)).toBe(false);
    expect(exceedsStock("60", null)).toBe(false);
  });
});

describe("etiquetas", () => {
  it("hay 14 locales, del 1 al 14, en una sola lista", () => {
    expect(Object.keys(LOCATION_OPTIONS)).toEqual(Array.from({ length: 14 }, (_, i) => String(i + 1)));
    expect(locationLabel(10)).toBe("Local 10");
  });

  it("las cantidades usan punto decimal y sin ceros sobrantes", () => {
    expect(formatAmount(52)).toBe("52");
    expect(formatAmount(40.5)).toBe("40.5");
    expect(formatAmount(0.1 + 0.2)).toBe("0.3");
    expect(formatQuantity(20, "litro")).toBe("20 litro");
  });
});
