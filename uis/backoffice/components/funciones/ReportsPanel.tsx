import { useState } from "react";
import Button from "@/components/Button";
import FormField from "@/components/FormField";
import LabeledSelect from "@/components/LabeledSelect";
import { CURRENCY_OPTIONS } from "@/lib/funciones/options";
import { funcionesApi, type Currency, type RunAction } from "@/lib/funciones/runner";

const GROUP_CLASS = "flex flex-col gap-2 rounded border border-red-200 p-3";
const GROUP_TITLE_CLASS = "text-sm font-semibold text-red-700";

export default function ReportsPanel({ run }: { run: RunAction }) {
  const [date, setDate] = useState("2024-03-15");
  const [currency, setCurrency] = useState<Currency>("USD");
  const [topN, setTopN] = useState("2");

  return (
    <section
      className="rounded-lg bg-white p-4 shadow-md lg:col-span-2"
      aria-labelledby="reportes-title"
    >
      <h2 id="reportes-title" className="mb-3 text-lg font-semibold text-red-700">
        Reportes y validaciones
      </h2>

      <div className="grid gap-2 md:grid-cols-2 lg:grid-cols-3">
        <div className={GROUP_CLASS}>
          <p className={GROUP_TITLE_CLASS}>Revenue diario</p>
          <FormField label="Fecha" type="date" value={date} onChange={setDate} />
          <LabeledSelect
            label="Moneda"
            value={currency}
            options={CURRENCY_OPTIONS}
            onChange={setCurrency}
            fullWidth
          />
          <Button
            onClick={() =>
              run("Revenue diario", () => funcionesApi.reports.dailyRevenue(date, currency))
            }
          >
            Ejecutar
          </Button>
        </div>

        <div className={GROUP_CLASS}>
          <p className={GROUP_TITLE_CLASS}>Ticket promedio / Método de pago</p>
          <Button
            onClick={() =>
              run("Ticket promedio", () => funcionesApi.reports.averageTicket(currency))
            }
          >
            Ticket promedio
          </Button>
          <Button
            variant="secondary"
            onClick={() =>
              run("Ventas por método de pago", () => funcionesApi.reports.salesByPaymentMethod())
            }
          >
            Ventas por método
          </Button>
        </div>

        <div className={GROUP_CLASS}>
          <p className={GROUP_TITLE_CLASS}>Top ítems vendidos</p>
          <FormField
            label="Cantidad"
            type="number"
            value={topN}
            onChange={setTopN}
            inputProps={{ min: 0 }}
          />
          <Button
            onClick={() =>
              run("Top ítems vendidos", () => funcionesApi.reports.topSellingItems(Number(topN)))
            }
          >
            Ejecutar
          </Button>
        </div>

        <div className={GROUP_CLASS}>
          <p className={GROUP_TITLE_CLASS}>Comparativa país / Ranking</p>
          <Button
            onClick={() =>
              run("Comparativa por país", () => funcionesApi.reports.countryComparison())
            }
          >
            Comparativa país
          </Button>
          <Button
            variant="secondary"
            onClick={() =>
              run("Ranking de locaciones", () => funcionesApi.reports.locationRanking())
            }
          >
            Ranking locaciones
          </Button>
        </div>

        <div className={GROUP_CLASS}>
          <p className={GROUP_TITLE_CLASS}>Validaciones de datos inválidos</p>
          <Button
            onClick={() =>
              run("Validación de ítem de menú", () => funcionesApi.validations.menuItem())
            }
          >
            Validar ítem de menú
          </Button>
          <Button onClick={() => run("Validación de venta", () => funcionesApi.validations.sale())}>
            Validar venta
          </Button>
          <Button
            onClick={() => run("Validación de locación", () => funcionesApi.validations.location())}
          >
            Validar locación
          </Button>
        </div>
      </div>
    </section>
  );
}
