// Catálogo de locales (lib/locations.ts): cliente, opciones del desplegable y la regla "un local solo
// registra ingredientes de su país" en los formularios. `fetch` está simulado: no hay red.
import {
  conflictsWithLocation,
  findLocation,
  ingredientListHint,
  ingredientsForLocation,
  listLocations,
  locationHintFor,
  locationName,
  locationOptions,
  removedIngredientNotice,
} from "@/lib/locations";
import type { Ingredient } from "@/types/inventory";
import type { Location } from "@/types/locations";

jest.mock("@/lib/auth/token", () => ({
  getToken: () => "jwt-de-la-sesion",
  clearToken: jest.fn(),
}));

const fetchMock = jest.fn();

beforeEach(() => {
  fetchMock.mockReset();
  global.fetch = fetchMock as unknown as typeof fetch;
});

const CENTRO: Location = { id: 1, code: "medellin_centro", name: "Medellín Centro", city: "Medellín", country: "CO", currency: "COP" };
const HIALEAH: Location = { id: 11, code: "miami_hialeah", name: "Miami Hialeah", city: "Miami", country: "US", currency: "USD" };
const LOCATIONS = [CENTRO, HIALEAH];

const BEEF: Ingredient = { id: 1, name: "Falda de ternera", sku: "BRS-BEEF-001", unit: "kg", category: "meat", country: "CO", current_stock: 52 };
const PORK: Ingredient = { id: 2, name: "Costilla de cerdo", sku: "BRS-PORK-001", unit: "kg", category: "meat", country: "US", current_stock: 32 };

describe("listLocations", () => {
  it("pide el catálogo al intermediario con el token", async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify(LOCATIONS), { status: 200, headers: { "Content-Type": "application/json" } }));

    await expect(listLocations()).resolves.toEqual(LOCATIONS);

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/locations");
    expect(new Headers(init.headers).get("Authorization")).toBe("Bearer jwt-de-la-sesion");
  });
});

describe("desplegable e historial", () => {
  it("cada opción es el id en texto con el nombre y el país del local", () => {
    expect(locationOptions(LOCATIONS)).toEqual({ "1": "Medellín Centro · Colombia", "11": "Miami Hialeah · Estados Unidos" });
  });

  it("findLocation busca por el valor del formulario", () => {
    expect(findLocation(LOCATIONS, "11")).toBe(HIALEAH);
    expect(findLocation(LOCATIONS, "")).toBeUndefined();
    expect(findLocation(LOCATIONS, "5")).toBeUndefined();
  });

  it("el historial muestra el nombre, y el número si el catálogo no cargó", () => {
    expect(locationName(LOCATIONS, 11)).toBe("Miami Hialeah");
    expect(locationName([], 11)).toBe("Local 11");
  });
});

describe("un local solo registra ingredientes de su país", () => {
  it("el local filtra los ingredientes; sin local se ofrecen todos", () => {
    expect(ingredientsForLocation([BEEF, PORK], CENTRO)).toEqual([BEEF]);
    expect(ingredientsForLocation([BEEF, PORK], HIALEAH)).toEqual([PORK]);
    expect(ingredientsForLocation([BEEF, PORK], undefined)).toEqual([BEEF, PORK]);
  });

  it("un ingrediente de otro país choca con el local; sin ingrediente o sin local, no", () => {
    expect(conflictsWithLocation(BEEF, HIALEAH)).toBe(true);
    expect(conflictsWithLocation(BEEF, CENTRO)).toBe(false);
    expect(conflictsWithLocation(undefined, HIALEAH)).toBe(false);
    expect(conflictsWithLocation(BEEF, undefined)).toBe(false);
  });
});

describe("textos de los formularios", () => {
  it("la ayuda del ingrediente dice para qué local es la lista", () => {
    expect(ingredientListHint(HIALEAH)).toBe("Solo ingredientes para Miami Hialeah.");
    expect(ingredientListHint(undefined)).toBe("Elige primero el local para ver solo los ingredientes de su país.");
  });

  it("con un ingrediente ya elegido y sin local, la ayuda del local dice cuáles lo conservan", () => {
    const base = "Local que recibe la entrega.";
    expect(locationHintFor(base, BEEF, undefined)).toBe(
      "Local que recibe la entrega. «Falda de ternera» es de Colombia: elige un local de Colombia para conservarlo."
    );
    expect(locationHintFor(base, BEEF, CENTRO)).toBe(base);
    expect(locationHintFor(base, undefined, undefined)).toBe(base);
  });

  it("avisa de que se quitó el ingrediente al elegir un local de otro país", () => {
    expect(removedIngredientNotice(BEEF, HIALEAH)).toBe(
      "Se quitó «Falda de ternera»: es un ingrediente de Colombia y Miami Hialeah está en Estados Unidos. Elige uno de la lista."
    );
  });
});
