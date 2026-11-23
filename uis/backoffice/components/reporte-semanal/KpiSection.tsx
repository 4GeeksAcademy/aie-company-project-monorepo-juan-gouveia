import {
  barPercent,
  COUNTRIES,
  formatKpi,
  locationsOf,
  rankBy,
  type KpiDefinition,
} from "@/lib/weekly-report";
import type { WeeklyLocationPerformance } from "@/types/weekly-report";

// Un KPI del briefing: su nombre, qué mide, y una barra por local de mayor a menor, separada por país.
// Cada barra lleva su valor escrito, así que los números no dependen del gráfico.
export default function KpiSection({ kpi, report }: { kpi: KpiDefinition; report: WeeklyLocationPerformance }) {
  const headingId = `kpi-${kpi.key}`;

  return (
    <section aria-labelledby={headingId} className="flex flex-col gap-3 rounded-lg border border-red-200 bg-white p-4 shadow-md">
      <div>
        <h2 id={headingId} className="text-lg font-semibold text-red-700">
          {kpi.label}
        </h2>
        <p className="text-sm text-black">{kpi.measures}</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {COUNTRIES.map(({ country, label, currency }) => {
          const rows = rankBy(locationsOf(report, country), kpi.key);
          if (rows.length === 0) return null;
          const max = Math.max(0, ...rows.map((row) => row[kpi.key]));
          return (
            <div key={country} className="flex flex-col gap-2">
              <h3 className="text-sm font-semibold text-black">
                {label}
                {kpi.kind === "money" && <span className="font-normal text-gray-600"> · en {currency}</span>}
              </h3>
              <ol className="flex flex-col gap-1.5">
                {rows.map((row) => (
                  <li key={row.location_id} className="grid grid-cols-[minmax(8rem,11rem)_1fr] items-center gap-2 text-sm">
                    <span className="truncate text-black" title={row.location_name}>
                      {row.location_name}
                    </span>
                    <span className="flex items-center gap-2">
                      <span className="h-3 flex-1 rounded-sm bg-red-50" aria-hidden="true">
                        <span
                          className="block h-3 rounded-sm bg-red-700"
                          style={{ width: `${barPercent(row[kpi.key], max)}%` }}
                        />
                      </span>
                      <span className="w-28 shrink-0 text-right tabular-nums text-black">
                        {formatKpi(kpi.kind, row[kpi.key], row.currency)}
                      </span>
                    </span>
                  </li>
                ))}
              </ol>
            </div>
          );
        })}
      </div>
    </section>
  );
}
