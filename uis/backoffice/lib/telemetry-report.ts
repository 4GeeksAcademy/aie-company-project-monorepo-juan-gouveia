import { ApiError, apiJson } from "@/lib/api-client";
import type { EventsPerDay, ReportDates, ReportLevel, TelemetryReport } from "@/types/telemetry-report";

// Reporte técnico de telemetría (plan de telemetría, sección 16): la vista /telemetria lo pide aquí y
// solo lo muestra. La ruta es la del intermediario (app/api/telemetry/report/route.ts), que la reenvía a
// GET /telemetry/report de la API, fuera de /api/v1. Es una vista técnica para ingeniería: no calcula
// métricas propias, solo da formato a las del reporte.

const REPORT_PATH = "/telemetry/report";
export const ADMIN_ONLY_MESSAGE = "Solo los administradores pueden ver el reporte técnico.";
const DATE_INPUT = /^\d{4}-\d{2}-\d{2}$/;
const DAY_MS = 24 * 60 * 60 * 1000;

// El día siguiente a una fecha YYYY-MM-DD, en UTC.
function nextDay(date: string): string {
  return new Date(Date.parse(`${date}T00:00:00Z`) + DAY_MS).toISOString().slice(0, 10);
}

// Query del reporte a partir de las fechas de la vista. En la vista las dos fechas se incluyen ("del 14
// al 16"); la API toma el fin como exclusivo, así que se envía el día siguiente al elegido.
export function reportQuery(dates: ReportDates): string {
  const params = new URLSearchParams();
  if (dates.from) params.set("start_date", dates.from);
  if (dates.to) params.set("end_date", nextDay(dates.to));
  const query = params.toString();
  return query ? `?${query}` : "";
}

// Error de las fechas antes de pedir nada, o null si se pueden enviar.
export function datesError(dates: ReportDates): string | null {
  if ((dates.from && !DATE_INPUT.test(dates.from)) || (dates.to && !DATE_INPUT.test(dates.to))) {
    return "Usa fechas con el formato AAAA-MM-DD.";
  }
  if (dates.from && dates.to && dates.from > dates.to) {
    return "La fecha inicial no puede ser posterior a la final.";
  }
  return null;
}

export async function getTelemetryReport(dates: ReportDates): Promise<TelemetryReport> {
  try {
    return await apiJson<TelemetryReport>(`${REPORT_PATH}${reportQuery(dates)}`, {
      fallback: "no se pudo cargar el reporte técnico",
    });
  } catch (error) {
    // 403: la sesión es válida pero el rol no es admin. No cierra la sesión (lo decide api-client).
    if (error instanceof ApiError && error.status === 403 && error.code !== "inactive_user") {
      throw new ApiError(ADMIN_ONLY_MESSAGE, 403, error.code, [], error.requestId);
    }
    throw error;
  }
}

// --- Presentación ------------------------------------------------------------------------------------------

export const LEVELS: ReportLevel[] = ["info", "warn", "error"];

export const LEVEL_LABELS: Record<ReportLevel, string> = {
  info: "Info",
  warn: "Aviso",
  error: "Error",
};

// Fecha y hora UTC de un límite del período. Ej.: "2026-11-13 14:19 UTC"; el texto tal cual si no se lee.
export function formatInstantUtc(iso: string): string {
  const time = Date.parse(iso);
  if (Number.isNaN(time)) return iso;
  return `${new Date(time).toISOString().slice(0, 16).replace("T", " ")} UTC`;
}

// Fracción de 0 a 1 como porcentaje con un decimal. Ej.: 0.3333 → "33.3%".
export function formatRate(rate: number): string {
  return `${(rate * 100).toFixed(1)}%`;
}

// Milisegundos con un decimal y separador de miles. Ej.: 2381.9 → "2,381.9 ms".
export function formatMs(ms: number): string {
  return `${ms.toLocaleString("en-US", { minimumFractionDigits: 1, maximumFractionDigits: 1 })} ms`;
}

// Ancho (en %) de una barra respecto al máximo de su serie; 0 si no hay máximo.
export function barPercent(value: number, max: number): number {
  if (max <= 0 || value <= 0) return 0;
  return Math.min(100, (value / max) * 100);
}

// Tramos de la barra apilada de un día: el ancho de cada nivel respecto al día con más eventos.
export function levelSegments(day: EventsPerDay, maxTotal: number): { level: ReportLevel; percent: number }[] {
  return LEVELS.map((level) => ({ level, percent: barPercent(day[level], maxTotal) })).filter((s) => s.percent > 0);
}

// Totales del período por nivel, para el resumen sobre el gráfico.
export function periodTotals(days: EventsPerDay[]): Record<ReportLevel | "total", number> {
  return days.reduce(
    (totals, day) => ({
      total: totals.total + day.total,
      info: totals.info + day.info,
      warn: totals.warn + day.warn,
      error: totals.error + day.error,
    }),
    { total: 0, info: 0, warn: 0, error: 0 },
  );
}
