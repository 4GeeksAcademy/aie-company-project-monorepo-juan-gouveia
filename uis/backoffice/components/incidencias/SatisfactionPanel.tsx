import BreakdownTable from "@/components/incidencias/BreakdownTable";
import { formatDecimal } from "@/lib/format";
import type { Satisfaction } from "@/types/incident";

export default function SatisfactionPanel({ satisfaction }: { satisfaction: Satisfaction }) {
  const { average, closed_cases, scored_cases, distribution } = satisfaction;

  return (
    <div className="flex flex-col gap-4">
      <section className="rounded-lg bg-white p-4 shadow-md">
        <h2 className="text-lg font-semibold text-red-700">
          Índice de satisfacción (casos cerrados)
        </h2>
        <p className="mt-1 text-sm text-black">
          Casos con puntaje: {scored_cases} de {closed_cases}
        </p>
        {average === null ? (
          <p className="mt-2 text-sm text-black">No hay casos con puntaje de satisfacción.</p>
        ) : (
          <p className="mt-2 text-black">
            <span className="text-sm">Puntaje promedio: </span>
            <span className="text-3xl font-semibold text-red-700">{formatDecimal(average)}</span>
            <span className="text-lg text-gray-600"> / {formatDecimal(5)}</span>
          </p>
        )}
      </section>

      <BreakdownTable
        title="Distribución de puntajes"
        itemHeader="Puntaje"
        caption="Porcentaje sobre los casos con puntaje."
        rows={distribution.map((item) => ({
          key: String(item.score),
          label: `Score ${item.score} (${item.label})`,
          count: item.count,
          percentage: item.percentage,
        }))}
      />
    </div>
  );
}
