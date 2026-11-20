import ReportTable, { Cell, NumericCell } from "@/components/telemetria/ReportTable";
import { formatRate, LEVEL_LABELS } from "@/lib/telemetry-report";
import type { ErrorRateByType } from "@/types/telemetry-report";

// error_rate_by_type: cada tipo de fallo de cada día, con su peso sobre el volumen de ese día.
export default function ErrorRateTable({ rows }: { rows: ErrorRateByType[] }) {
  return (
    <ReportTable
      columns={[{ label: "Día" }, { label: "Tipo de evento" }, { label: "Nivel" }, { label: "Eventos", numeric: true }, { label: "Del día", numeric: true }]}
    >
      {rows.map((row) => (
        <tr key={`${row.date}-${row.event_type}`}>
          <Cell>{row.date}</Cell>
          <Cell>
            <code className="break-all">{row.event_type}</code>
          </Cell>
          <Cell>
            <span className={row.level === "error" ? "font-semibold text-red-700" : "text-amber-700"}>{LEVEL_LABELS[row.level]}</span>
          </Cell>
          <NumericCell>{row.count}</NumericCell>
          <NumericCell>{formatRate(row.rate)}</NumericCell>
        </tr>
      ))}
    </ReportTable>
  );
}
