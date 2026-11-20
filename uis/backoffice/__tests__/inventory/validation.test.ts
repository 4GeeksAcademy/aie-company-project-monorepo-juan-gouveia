// Validación en el cliente de los formularios de entrada y salida (lib/inventory-validation.ts) y
// las utilidades de etiquetas del inventario (lib/inventory-labels.ts).
import { ApiError } from "@/lib/api-client";
import { formatAmount, formatQuantity } from "@/lib/inventory-labels";
import {
  EMPTY_ENTRY_FORM,
  EMPTY_EXIT_FORM,
  exceedsStock,
  exitErrorsFromApi,
  parseQuantity,
  presetIngredientId,
  toEntryInput,
  toExitInput,
  validateEntryForm,
  validateExitForm,
} from "@/lib/inventory-validation";

const VALID_ENTRY = { ingredient_id: "1", quantity: "50", supplier_name: "  Carnes del Valle S.A. ", unit_cost: "38500", location_id: "1" };
const VALID_EXIT = { ingredient_id: "1", quantity: "3,5", reason: "waste" as const, waste_reason: "expired" as const, location_id: "14" };

describe("exitErrorsFromApi", () => {
  it("coloca el 400 insufficient_stock junto a la cantidad", () => {
    const message = "Stock insuficiente para el ingrediente 'Yuca'. Disponible: 0, solicitado: 3.";
    expect(exitErrorsFromApi(new ApiError(message, 400, "insufficient_stock"))).toEqual({
      fields: { quantity: message },
      message: "Revisa los campos marcados.",
    });
  });

  it("reparte los 422 por campo, como formErrorsFromApi", () => {
    const err = new ApiError("La petición no es válida.", 422, "invalid_request", [
      { field: "quantity", message: "Debe ser mayor que 0." },
      { field: "reason", message: "Valor no permitido." },
    ]);
    expect(exitErrorsFromApi(err)).toEqual({
      fields: { quantity: "Debe ser mayor que 0.", reason: "Valor no permitido." },
      message: "Revisa los campos marcados.",
    });
  });

  it("deja los demás errores en el aviso general", () => {
    const err = new ApiError("No existe ningún ingrediente con el ID 999.", 404, "ingredient_not_found");
    expect(exitErrorsFromApi(err)).toEqual({ fields: {}, message: "No existe ningún ingrediente con el ID 999." });
  });
});

describe("presetIngredientId", () => {
  it.each([
    ["1", "1"],
    ["42", "42"],
    [" 7 ", "7"],
  ])("acepta %p como %p", (raw, expected) => {
    expect(presetIngredientId(raw)).toBe(expected);
  });

  it.each([[undefined], [""], ["0"], ["-3"], ["1.5"], ["abc"], ["01"], [["1", "2"]]])(
    "descarta %p",
    (raw) => {
      expect(presetIngredientId(raw)).toBe("");
    }
  );
});

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

  it("vacío marca los cinco campos", () => {
    expect(Object.keys(validateEntryForm(EMPTY_ENTRY_FORM)).sort()).toEqual(
      ["ingredient_id", "location_id", "quantity", "supplier_name", "unit_cost"].sort()
    );
  });

  it.each([
    [{ quantity: "0" }, "quantity", "La cantidad debe ser mayor que 0."],
    [{ quantity: "doce" }, "quantity", "Escribe un número, por ejemplo 12 o 12.5."],
    [{ supplier_name: "   " }, "supplier_name", "Elige el proveedor."],
    [{ supplier_name: "x".repeat(121) }, "supplier_name", "El proveedor no puede superar 120 caracteres."],
    [{ location_id: "15" }, "location_id", "Elige el local."],
    [{ unit_cost: "" }, "unit_cost", "Escribe el coste por unidad."],
    [{ unit_cost: "0" }, "unit_cost", "El coste debe ser mayor que 0."],
    [{ unit_cost: "caro" }, "unit_cost", "Escribe un número, por ejemplo 38500 o 6.8."],
  ])("con %p marca %s", (changes, field, message) => {
    expect(validateEntryForm({ ...VALID_ENTRY, ...changes })).toEqual({ [field]: message });
  });

  it("toEntryInput convierte los textos al cuerpo de la API", () => {
    expect(toEntryInput(VALID_ENTRY)).toEqual({
      ingredient_id: 1,
      quantity: 50,
      supplier_name: "Carnes del Valle S.A.",
      unit_cost: 38500,
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

  it("toExitInput admite la coma decimal y envía el motivo de la merma", () => {
    expect(toExitInput(VALID_EXIT)).toEqual({ ingredient_id: 1, quantity: 3.5, reason: "waste", waste_reason: "expired", location_id: 14 });
  });

  it("una merma sin motivo marca waste_reason", () => {
    expect(validateExitForm({ ...VALID_EXIT, waste_reason: "" })).toEqual({ waste_reason: "Elige el motivo de la merma." });
  });

  it("un consumo no necesita motivo de merma y no lo envía aunque quede uno elegido", () => {
    const consumption = { ...VALID_EXIT, reason: "consumption" as const };
    expect(validateExitForm({ ...consumption, waste_reason: "" })).toEqual({});
    expect(toExitInput(consumption)).not.toHaveProperty("waste_reason");
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
  it("las cantidades usan punto decimal y sin ceros sobrantes", () => {
    expect(formatAmount(52)).toBe("52");
    expect(formatAmount(40.5)).toBe("40.5");
    expect(formatAmount(0.1 + 0.2)).toBe("0.3");
    expect(formatQuantity(20, "litro")).toBe("20 litro");
  });
});
