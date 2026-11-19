import { useEffect, useState } from "react";
import { toUserMessage } from "@/lib/error-message";
import { activeSupplierNames, supplierFiltersFor } from "@/lib/inventory-suppliers";
import { listSuppliers } from "@/lib/proveedores/api";
import type { Ingredient } from "@/types/inventory";

// Cada estado recuerda de qué ingrediente es: así nunca se ofrecen los proveedores de uno anterior.
type SuppliersState =
  | { id: number; status: "loading" }
  | { id: number; status: "error"; message: string }
  // idsByName: id de cada proveedor en el directorio, para la telemetría (`supplier_id`; la entrada
  // solo guarda el nombre, que es único en el directorio).
  | { id: number; status: "success"; names: string[]; idsByName: Record<string, number> };

export type IngredientSuppliers = { status: "idle" } | SuppliersState;

// Proveedores activos del directorio que pueden entregar el ingrediente elegido en el formulario de
// entrada: mismo país y categoría equivalente (lib/inventory-suppliers.ts). Se piden a la API
// (GET /suppliers?country=&category=) cada vez que cambia el ingrediente; si el usuario cambia antes
// de que llegue la respuesta, la anterior se descarta.
export function useIngredientSuppliers(ingredient: Ingredient | undefined) {
  const [state, setState] = useState<SuppliersState | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const id = ingredient?.id;
  const category = ingredient?.category;
  const country = ingredient?.country;

  useEffect(() => {
    if (id === undefined || !category || !country) return;
    let cancelled = false;

    async function load(ingredientId: number, filters: ReturnType<typeof supplierFiltersFor>) {
      setState({ id: ingredientId, status: "loading" });
      try {
        const suppliers = await listSuppliers(filters);
        if (cancelled) return;
        const names = activeSupplierNames(suppliers);
        const idsByName = Object.fromEntries(suppliers.filter((s) => names.includes(s.name)).map((s) => [s.name, s.id]));
        setState({ id: ingredientId, status: "success", names, idsByName });
      } catch (err) {
        if (cancelled) return;
        setState({
          id: ingredientId,
          status: "error",
          message: toUserMessage(err, "No se pudieron cargar los proveedores."),
        });
      }
    }

    load(id, supplierFiltersFor({ category, country }));
    return () => {
      cancelled = true;
    };
  }, [id, category, country, reloadKey]);

  // Sin ingrediente no hay nada que ofrecer; con un estado de otro ingrediente, se está cargando.
  let suppliers: IngredientSuppliers;
  if (id === undefined) suppliers = { status: "idle" };
  else if (!state || state.id !== id) suppliers = { id, status: "loading" };
  else suppliers = state;

  return { suppliers, reload: () => setReloadKey((key) => key + 1) };
}
