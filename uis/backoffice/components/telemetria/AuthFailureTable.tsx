import ReportTable, { Cell, NumericCell } from "@/components/telemetria/ReportTable";
import { formatRate } from "@/lib/telemetry-report";
import type { AuthFailureRate } from "@/types/telemetry-report";

// auth_failure_rate: intentos de login de cada día y la parte que falló.
export default function AuthFailureTable({ rows }: { rows: AuthFailureRate[] }) {
  return (
    <ReportTable
      columns={[{ label: "Día" }, { label: "Intentos", numeric: true }, { label: "Fallidos", numeric: true }, { label: "Tasa de fallo", numeric: true }]}
    >
      {rows.map((row) => (
        <tr key={row.date}>
          <Cell>{row.date}</Cell>
          <NumericCell>{row.attempts}</NumericCell>
          <NumericCell>{row.failed}</NumericCell>
          <NumericCell>{formatRate(row.failure_rate)}</NumericCell>
        </tr>
      ))}
    </ReportTable>
  );
}
