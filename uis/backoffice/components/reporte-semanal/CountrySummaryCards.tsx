import { formatCount, formatMoney, formatRatio, KPIS, type CountrySummary } from "@/lib/weekly-report";

// El consolidado por país, lado a lado: cada país en su moneda, nunca sumados entre sí (briefing, §7).
export default function CountrySummaryCards({ summaries }: { summaries: CountrySummary[] }) {
  const label = (key: (typeof KPIS)[number]["key"]) => KPIS.find((kpi) => kpi.key === key)?.label ?? key;

  return (
    <section aria-labelledby="resumen-por-pais" className="flex flex-col gap-3">
      <h2 id="resumen-por-pais" className="text-lg font-semibold text-red-700">
        Resumen por país
      </h2>
      <div className="grid gap-4 md:grid-cols-2">
        {summaries.map((summary) => (
          <article key={summary.country} className="rounded-lg border border-red-200 bg-white p-4 shadow-md">
            <h3 className="text-base font-semibold text-black">
              {summary.label} <span className="font-normal text-gray-600">· {summary.locations} locales · en {summary.currency}</span>
            </h3>
            <dl className="mt-3 grid grid-cols-1 gap-2 text-sm sm:grid-cols-2">
              <div>
                <dt className="text-gray-600">Costo de compra</dt>
                <dd className="text-lg font-semibold text-black">{formatMoney(summary.total_purchase_cost, summary.currency)}</dd>
              </div>
              <div>
                <dt className="text-gray-600">Costo de merma</dt>
                <dd className="text-lg font-semibold text-black">{formatMoney(summary.total_waste_cost, summary.currency)}</dd>
              </div>
              <div>
                <dt className="text-gray-600">{label("waste_ratio")}</dt>
                <dd className="text-lg font-semibold text-black">{formatRatio(summary.waste_ratio)}</dd>
              </div>
              <div>
                <dt className="text-gray-600">Quiebres de stock · alertas de precio</dt>
                <dd className="text-lg font-semibold text-black">
                  {formatCount(summary.stockout_events_count)} · {formatCount(summary.price_alert_events_count)}
                </dd>
              </div>
            </dl>
          </article>
        ))}
      </div>
    </section>
  );
}
