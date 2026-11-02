import { useState } from "react";
import Button from "@/components/Button";
import FormField from "@/components/FormField";
import LabeledSelect from "@/components/LabeledSelect";
import { CURRENCY_OPTIONS, ORDER_OPTIONS } from "@/lib/funciones/options";
import { funcionesApi, type Currency, type Order, type RunAction } from "@/lib/funciones/runner";

export default function SearchSortPanel({ run }: { run: RunAction }) {
  const [locationId, setLocationId] = useState("LOC-MIAMI-01");
  const [itemName, setItemName] = useState("Coca-Cola");
  const [capacity, setCapacity] = useState("100");
  const [currency, setCurrency] = useState<Currency>("USD");
  const [order, setOrder] = useState<Order>("asc");

  return (
    <section className="rounded-lg bg-white p-4 shadow-md" aria-labelledby="buscar-title">
      <h2 id="buscar-title" className="mb-3 text-lg font-semibold text-red-700">
        Buscar y ordenar
      </h2>

      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-2">
          <FormField label="ID de locación" value={locationId} onChange={setLocationId} />
          <Button
            onClick={() =>
              run("Búsqueda de locación por ID", () => funcionesApi.search.locationById(locationId))
            }
          >
            Buscar locación
          </Button>
        </div>

        <div className="flex flex-col gap-2">
          <FormField label="Nombre del ítem" value={itemName} onChange={setItemName} />
          <Button
            onClick={() =>
              run("Búsqueda de ítem por nombre", () =>
                funcionesApi.search.menuItemByName(itemName),
              )
            }
          >
            Buscar ítem
          </Button>
        </div>

        <div className="flex flex-col gap-2">
          <FormField label="Capacidad" type="number" value={capacity} onChange={setCapacity} />
          <Button
            onClick={() =>
              run("Búsqueda binaria por capacidad", () =>
                funcionesApi.search.locationCapacityBinary(Number(capacity)),
              )
            }
          >
            Búsqueda binaria
          </Button>
        </div>

        <div className="flex flex-col gap-2">
          <div className="grid grid-cols-2 gap-2">
            <LabeledSelect
              label="Moneda"
              value={currency}
              options={CURRENCY_OPTIONS}
              onChange={setCurrency}
              fullWidth
            />
            <LabeledSelect
              label="Orden"
              value={order}
              options={ORDER_OPTIONS}
              onChange={setOrder}
              fullWidth
            />
          </div>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            <Button
              variant="secondary"
              onClick={() =>
                run("Locaciones ordenadas por capacidad", () =>
                  funcionesApi.sort.locationsByCapacity(order),
                )
              }
            >
              Ordenar locaciones
            </Button>
            <Button
              variant="secondary"
              onClick={() =>
                run("Ítems ordenados por precio", () =>
                  funcionesApi.sort.menuItemsByPrice(currency, order),
                )
              }
            >
              Ordenar ítems
            </Button>
          </div>
        </div>
      </div>
    </section>
  );
}
