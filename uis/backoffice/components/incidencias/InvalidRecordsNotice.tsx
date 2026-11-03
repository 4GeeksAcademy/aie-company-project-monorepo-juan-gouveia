import { ruleLabel } from "@/lib/incidencias/labels";
import type { IncidentAnalysis } from "@/types/incident";

type InvalidRecordsNoticeProps = Pick<
  IncidentAnalysis,
  "invalid_records" | "invalid_breakdown" | "invalid_records_detail"
>;

// Explica qué registros quedaron fuera del análisis y por qué.
export default function InvalidRecordsNotice({
  invalid_records,
  invalid_breakdown,
  invalid_records_detail,
}: InvalidRecordsNoticeProps) {
  if (invalid_records === 0) {
    return (
      <p
        role="status"
        className="rounded-lg border border-green-200 bg-green-50 p-4 text-sm text-green-800 md:text-base"
      >
        Todos los registros son válidos y se incluyeron en el análisis.
      </p>
    );
  }

  // La API envía todas las reglas; solo se muestran las que se incumplieron.
  const brokenRules = invalid_breakdown.filter((item) => item.count > 0);
  const labels = new Map(invalid_breakdown.map((item) => [item.rule, item.label]));

  return (
    <section
      aria-labelledby="invalidos-title"
      className="rounded-lg border border-amber-300 bg-amber-50 p-4 text-amber-900"
    >
      <h2 id="invalidos-title" className="font-semibold md:text-lg">
        {invalid_records === 1
          ? "1 registro no se incluyó en el análisis"
          : `${invalid_records} registros no se incluyeron en el análisis`}
      </h2>
      <p className="mt-1 text-sm">
        Los totales por categoría, estado y satisfacción solo cuentan los registros válidos. Corrige
        estos registros en el archivo y vuelve a subirlo para incluirlos.
      </p>

      <h3 className="mt-3 text-sm font-semibold">Desglose de registros inválidos</h3>
      <ul className="mt-1 flex flex-col gap-1 text-sm">
        {brokenRules.map((item) => (
          <li key={item.rule} className="flex justify-between gap-4">
            <span>{ruleLabel(item.rule, item.label)}</span>
            <span className="font-semibold tabular-nums">{item.count}</span>
          </li>
        ))}
      </ul>
      {brokenRules.length > 1 && (
        <p className="mt-2 text-xs">Un registro puede incumplir más de un motivo.</p>
      )}

      <details className="mt-3 text-sm">
        <summary className="cursor-pointer font-semibold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-700">
          Ver los registros inválidos
        </summary>
        <div className="mt-2 overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-amber-300">
                <th scope="col" className="py-2 pr-2 font-medium">
                  ID
                </th>
                <th scope="col" className="px-2 py-2 font-medium">
                  Fila
                </th>
                <th scope="col" className="py-2 pl-2 font-medium">
                  Motivos
                </th>
              </tr>
            </thead>
            <tbody>
              {invalid_records_detail.map((record) => (
                <tr key={record.row} className="border-b border-amber-200 last:border-0 align-top">
                  <td className="py-2 pr-2 font-mono whitespace-nowrap">
                    {record.incident_id || "(sin ID)"}
                  </td>
                  <td className="px-2 py-2 tabular-nums">{record.row}</td>
                  <td className="py-2 pl-2">
                    {record.rules.map((rule) => ruleLabel(rule, labels.get(rule))).join("; ")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </section>
  );
}
