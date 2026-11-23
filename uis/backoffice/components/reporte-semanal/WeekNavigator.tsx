import Button from "@/components/Button";
import { formatWeekPeriod, shiftWeek } from "@/lib/weekly-report";

interface WeekNavigatorProps {
  // Lunes de la semana mostrada (YYYY-MM-DD).
  weekStart: string;
  // Lunes de la semana en curso: no se puede ir más allá.
  currentWeek: string;
  onShowWeek: (weekStart: string) => void;
  disabled?: boolean;
}

// El período del reporte en palabras y los botones para ir a la semana anterior o a la siguiente.
export default function WeekNavigator({ weekStart, currentWeek, onShowWeek, disabled = false }: WeekNavigatorProps) {
  const previous = shiftWeek(weekStart, -1);
  const next = shiftWeek(weekStart, 1);

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-red-200 bg-white p-4 shadow-md md:flex-row md:items-center md:justify-between">
      <p className="text-lg font-semibold text-black" aria-live="polite">
        <time dateTime={weekStart}>{formatWeekPeriod(weekStart)}</time>
      </p>
      <div className="flex gap-2">
        <Button variant="secondary" onClick={() => onShowWeek(previous)} disabled={disabled}>
          ← Semana anterior
        </Button>
        <Button variant="secondary" onClick={() => onShowWeek(next)} disabled={disabled || next > currentWeek}>
          Semana siguiente →
        </Button>
      </div>
    </div>
  );
}
