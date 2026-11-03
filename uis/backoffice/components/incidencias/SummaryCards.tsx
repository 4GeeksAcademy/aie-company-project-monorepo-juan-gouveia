import type { IncidentAnalysis } from "@/types/incident";

interface SummaryCardProps {
  label: string;
  value: number;
  tone?: "default" | "warning";
}

function SummaryCard({ label, value, tone = "default" }: SummaryCardProps) {
  return (
    <div className="rounded-lg bg-white p-4 shadow-md">
      <dt className="text-sm text-black">{label}</dt>
      <dd
        className={`mt-1 text-2xl font-semibold md:text-3xl ${tone === "warning" ? "text-amber-700" : "text-red-700"}`}
      >
        {value}
      </dd>
    </div>
  );
}

export default function SummaryCards({ result }: { result: IncidentAnalysis }) {
  return (
    <dl className="grid grid-cols-1 gap-4 sm:grid-cols-3">
      <SummaryCard label="Total de registros en el archivo" value={result.total_records} />
      <SummaryCard label="Registros válidos" value={result.valid_records} />
      <SummaryCard
        label="Registros inválidos o incompletos"
        value={result.invalid_records}
        tone={result.invalid_records > 0 ? "warning" : "default"}
      />
    </dl>
  );
}
