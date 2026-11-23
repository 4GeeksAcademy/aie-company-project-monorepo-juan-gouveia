import { apiJson } from "@/lib/api-client";
import { COUNTRY_DESCRIPTIONS } from "@/lib/inventory-labels";
import type { Ingredient } from "@/types/inventory";
import type { Location } from "@/types/locations";

// Catálogo de los 14 locales de Brasaland, leído de la API (tabla `locations`). Es la única fuente de
// los nombres y del país de cada local: sustituye a la lista "Local 1"…"Local 14" de la decisión F5.
//
// Regla del inventario: un local solo registra ingredientes de su país (la API responde 422
// `location_country_mismatch` si no). Los formularios la aplican antes de enviar: el local filtra los
// ingredientes, y elegir un local de otro país descarta el ingrediente elegido.

// GET /locations, por el intermediario (/api/locations → /api/v1/locations).
export function listLocations(): Promise<Location[]> {
  return apiJson("/locations", { fallback: "no se pudieron cargar los locales" });
}

// Opciones del desplegable: el id en texto ("1"…"14") y el nombre con su país.
export function locationOptions(locations: Location[]): Record<string, string> {
  return Object.fromEntries(
    locations.map((location) => [String(location.id), `${location.name} · ${COUNTRY_DESCRIPTIONS[location.country]}`])
  );
}

// El local elegido en un formulario (su id en texto), o undefined si no hay ninguno o no existe.
export function findLocation(locations: Location[], idText: string): Location | undefined {
  return locations.find((location) => String(location.id) === idText);
}

// Nombre del local para el historial. Sin catálogo (cargando o con error), el número.
export function locationName(locations: Location[], id: number): string {
  return locations.find((location) => location.id === id)?.name ?? `Local ${id}`;
}

// Ingredientes que puede registrar el local: los de su país. Sin local elegido, todos.
export function ingredientsForLocation(ingredients: Ingredient[], location: Location | undefined): Ingredient[] {
  return location ? ingredients.filter((ingredient) => ingredient.country === location.country) : ingredients;
}

// true si el ingrediente elegido no es del país del local: el formulario lo descarta al cambiar de local.
export function conflictsWithLocation(ingredient: Ingredient | undefined, location: Location | undefined): boolean {
  return Boolean(ingredient && location && ingredient.country !== location.country);
}

// --- Textos de los formularios ------------------------------------------------------------------

// Bajo el selector de ingrediente: qué ingredientes ofrece la lista.
export function ingredientListHint(location: Location | undefined): string {
  return location
    ? `Solo ingredientes para ${location.name}.`
    : "Elige primero el local para ver solo los ingredientes de su país.";
}

// Bajo el selector de local, si ya hay un ingrediente (p. ej. el del enlace) y aún no hay local.
export function locationHintFor(base: string, ingredient: Ingredient | undefined, location: Location | undefined): string {
  if (!ingredient || location) return base;
  const country = COUNTRY_DESCRIPTIONS[ingredient.country];
  return `${base} «${ingredient.name}» es de ${country}: elige un local de ${country} para conservarlo.`;
}

// Aviso cuando elegir un local de otro país descarta el ingrediente elegido.
export function removedIngredientNotice(ingredient: Ingredient, location: Location): string {
  return (
    `Se quitó «${ingredient.name}»: es un ingrediente de ${COUNTRY_DESCRIPTIONS[ingredient.country]} y ` +
    `${location.name} está en ${COUNTRY_DESCRIPTIONS[location.country]}. Elige uno de la lista.`
  );
}
