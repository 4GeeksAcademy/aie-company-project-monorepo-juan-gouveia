import { LEVEL_LABELS, LEVELS, levelSegments, periodTotals } from "@/lib/telemetry-report";
import type { EventsPerDay, ReportLevel } from "@/types/telemetry-report";

const LEVEL_COLORS: Record<ReportLevel, string> = {
  info: "bg-gray-400",
  warn: "bg-amber-500",
  error: "bg-red-700",
};

// events_per_day: una barra horizontal por día, apilada por nivel y proporcional al día con más
// eventos. Cada fila lleva su desglose en texto, así que los números no dependen del color.
export default function EventsPerDayChart({ days }: { days: EventsPerDay[] }) {
  const maxTotal = Math.max(0, ...days.map((day) => day.total));
  const totals = periodTotals(days);

  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-black">
        {totals.total} eventos en el período: {totals.info} info, {totals.warn} avisos y {totals.error} errores.
      </p>

      <ul className="flex flex-wrap gap-4 text-xs text-black" aria-label="Leyenda">
        {LEVELS.map((level) => (
          <li key={level} className="flex items-center gap-1">
            <span aria-hidden="true" className={`inline-block h-3 w-3 rounded-sm ${LEVEL_COLORS[level]}`} />
            {LEVEL_LABELS[level]}
          </li>
        ))}
      </ul>

      <ul className="flex flex-col gap-2">
        {days.map((day) => (
          <li key={day.date} className="grid grid-cols-[6.5rem_minmax(0,1fr)] items-center gap-2 text-sm md:grid-cols-[6.5rem_minmax(0,1fr)_14rem]">
            <span className="tabular-nums text-black">{day.date}</span>
            <div
              className="flex h-4 overflow-hidden rounded-sm bg-red-50"
              role="img"
              aria-label={`${day.date}: ${day.total} eventos (${day.info} info, ${day.warn} avisos, ${day.error} errores)`}
            >
              {levelSegments(day, maxTotal).map((segment) => (
                <span key={segment.level} className={LEVEL_COLORS[segment.level]} style={{ width: `${segment.percent}%` }} />
              ))}
            </div>
            <span className="col-start-2 text-xs tabular-nums text-black md:col-start-auto">
              {day.total} · {day.info} info · {day.warn} avisos · {day.error} errores
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
