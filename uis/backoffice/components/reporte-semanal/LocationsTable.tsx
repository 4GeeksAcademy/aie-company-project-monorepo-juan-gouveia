import { COUNTRIES, formatKpi, KPIS, locationsOf } from "@/lib/weekly-report";
import type { WeeklyLocationPerformance } from "@/types/weekly-report";

// Los 14 locales con los cinco KPIs, agrupados por país y cada uno en su moneda.
export default function LocationsTable({ report }: { report: WeeklyLocationPerformance }) {
  return (
    <section aria-labelledby="todos-los-locales" className="flex flex-col gap-3 rounded-lg border border-red-200 bg-white p-4 shadow-md">
      <h2 id="todos-los-locales" className="text-lg font-semibold text-red-700">
        Todos los locales
      </h2>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[48rem] text-left text-sm text-black">
          <thead>
            <tr className="border-b border-red-200 text-xs text-gray-600">
              <th scope="col" className="py-2 pr-3 font-semibold">
                Local
              </th>
              {KPIS.map((kpi) => (
                <th key={kpi.key} scope="col" className="py-2 pr-3 text-right font-semibold">
                  {kpi.label}
                </th>
              ))}
              <th scope="col" className="py-2 font-semibold">
                Moneda
              </th>
            </tr>
          </thead>
          {COUNTRIES.map(({ country, label }) => {
            const rows = locationsOf(report, country);
            if (rows.length === 0) return null;
            return (
              <tbody key={country}>
                <tr>
                  <th scope="rowgroup" colSpan={KPIS.length + 2} className="bg-red-50 px-2 py-1.5 text-left font-semibold text-red-700">
                    {label}
                  </th>
                </tr>
                {rows.map((row) => (
                  <tr key={row.location_id} className="border-b border-gray-100">
                    <th scope="row" className="py-1.5 pr-3 font-normal">
                      {row.location_name}
                    </th>
                    {KPIS.map((kpi) => (
                      <td key={kpi.key} className="py-1.5 pr-3 text-right tabular-nums">
                        {formatKpi(kpi.kind, row[kpi.key], row.currency)}
                      </td>
                    ))}
                    <td className="py-1.5">{row.currency}</td>
                  </tr>
                ))}
              </tbody>
            );
          })}
        </table>
      </div>
    </section>
  );
}
