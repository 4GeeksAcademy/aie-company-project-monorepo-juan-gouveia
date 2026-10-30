import { useState } from "react";
import type { MenuCategory } from "@repo/brasa-core";
import Button from "@/components/Button";
import FormField from "@/components/FormField";
import LabeledSelect from "@/components/LabeledSelect";
import { funcionesApi, type RunAction } from "@/lib/funciones/runner";

const CATEGORY_OPTIONS: Record<MenuCategory, string> = {
  Meat: "Meat",
  Side: "Side",
  Beverage: "Beverage",
  Dessert: "Dessert",
  Combo: "Combo",
};

export default function FilterPanel({ run }: { run: RunAction }) {
  const [locationId, setLocationId] = useState("LOC-MEDELLIN-01");
  const [startDate, setStartDate] = useState("2024-03-15T00:00");
  const [endDate, setEndDate] = useState("2024-03-15T23:59");
  const [category, setCategory] = useState<MenuCategory>("Meat");

  return (
    <section className="rounded-lg bg-white p-4 shadow-md" aria-labelledby="filtrar-title">
      <h2 id="filtrar-title" className="mb-3 text-lg font-semibold text-red-700">
        Filtrar
      </h2>

      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-2">
          <FormField label="ID de locación" value={locationId} onChange={setLocationId} />
          <Button
            onClick={() =>
              run("Ventas por locación", () => funcionesApi.filters.salesByLocation(locationId))
            }
          >
            Ventas por locación
          </Button>
        </div>

        <div className="flex flex-col gap-2">
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            <FormField
              label="Desde"
              type="datetime-local"
              value={startDate}
              onChange={setStartDate}
            />
            <FormField label="Hasta" type="datetime-local" value={endDate} onChange={setEndDate} />
          </div>
          <Button
            onClick={() =>
              run("Ventas por rango de fechas", () =>
                funcionesApi.filters.salesByDateRange(startDate, endDate),
              )
            }
          >
            Ventas por rango
          </Button>
        </div>

        <div className="flex flex-col gap-2">
          <LabeledSelect
            label="Categoría"
            value={category}
            options={CATEGORY_OPTIONS}
            onChange={setCategory}
            fullWidth
          />
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            <Button
              onClick={() =>
                run("Ítems por categoría", () => funcionesApi.filters.menuByCategory(category))
              }
            >
              Ítems por categoría
            </Button>
            <Button
              variant="secondary"
              onClick={() =>
                run("Locaciones activas", () => funcionesApi.filters.activeLocations())
              }
            >
              Locaciones activas
            </Button>
          </div>
        </div>
      </div>
    </section>
  );
}
