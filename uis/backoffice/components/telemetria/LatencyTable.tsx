import ReportTable, { Cell, NumericCell } from "@/components/telemetria/ReportTable";
import { barPercent, formatMs } from "@/lib/telemetry-report";
import type { ApiLatencyByRoute } from "@/types/telemetry-report";

// api_latency_by_route: la latencia de cada ruta de la API por día, de la más lenta a la más rápida.
// La barra compara la media de cada fila con la mayor del período.
export default function LatencyTable({ rows }: { rows: ApiLatencyByRoute[] }) {
  const maxAvg = Math.max(0, ...rows.map((row) => row.avg_ms));

  return (
    <ReportTable
      columns={[
        { label: "Día" },
        { label: "Ruta" },
        { label: "Muestras", numeric: true },
        { label: "Media", numeric: true },
        { label: "Máximo", numeric: true },
      ]}
    >
      {rows.map((row) => (
        <tr key={`${row.date}-${row.method}-${row.route}`}>
          <Cell>{row.date}</Cell>
          <Cell>
            <code className="break-all">
              {row.method} {row.route}
            </code>
            <span aria-hidden="true" className="mt-1 block h-1.5 rounded-sm bg-red-50">
              <span className="block h-1.5 rounded-sm bg-red-700" style={{ width: `${barPercent(row.avg_ms, maxAvg)}%` }} />
            </span>
          </Cell>
          <NumericCell>{row.samples}</NumericCell>
          <NumericCell>{formatMs(row.avg_ms)}</NumericCell>
          <NumericCell>{formatMs(row.max_ms)}</NumericCell>
        </tr>
      ))}
    </ReportTable>
  );
}
