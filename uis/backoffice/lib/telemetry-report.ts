import { ApiError, apiJson, jsonBody } from "@/lib/api-client";
import type { TaskAccepted, TaskStatus } from "@/types/tasks";
import type { EventsPerDay, ReportDates, ReportLevel, TelemetryReport } from "@/types/telemetry-report";

// Reporte técnico de telemetría (plan de telemetría, sección 16): la vista /telemetria lo pide aquí y
// solo lo muestra. Es una vista técnica para ingeniería: no calcula métricas propias, solo da formato a
// las del reporte.
//
// Desde el ticket #DEV-55 el reporte es una tarea asíncrona (decisión T13): POST /telemetry/report lo
// encola y responde 202 con el task_id, y aquí se consulta GET /tasks/{task_id} cada 1 s (cada 2 s pasados
// 10 s) hasta que termina, con un tope de 3 min, más que el peor caso de los reintentos (~70 s). Las dos
// rutas son las del intermediario (app/api/telemetry/report y app/api/tasks/[taskId]), que las reenvían a
// la API, fuera de /api/v1.

const REPORT_PATH = "/telemetry/report";
const TASKS_PATH = "/tasks";
export const ADMIN_ONLY_MESSAGE = "Solo los administradores pueden ver el reporte técnico.";
export const SLOW_REPORT_MESSAGE =
  "El informe está tardando más de lo normal. Vuelve a intentarlo en unos minutos; si continúa, avisa al equipo técnico.";
const DATE_INPUT = /^\d{4}-\d{2}-\d{2}$/;
const DAY_MS = 24 * 60 * 60 * 1000;

export const POLL_FAST_MS = 1_000;
export const POLL_SLOW_MS = 2_000;
export const POLL_FAST_PHASE_MS = 10_000;
export const POLL_TIMEOUT_MS = 3 * 60 * 1_000;

// Estado de una tarea que todavía no terminó, para la vista ("En cola" o "Calculando").
export type ReportProgress = "pending" | "started";

// El día siguiente a una fecha YYYY-MM-DD, en UTC.
function nextDay(date: string): string {
  return new Date(Date.parse(`${date}T00:00:00Z`) + DAY_MS).toISOString().slice(0, 10);
}

// Cuerpo de POST /telemetry/report a partir de las fechas de la vista. En la vista las dos fechas se
// incluyen ("del 14 al 16"); la API toma el fin como exclusivo, así que se envía el día siguiente al
// elegido. Sin fechas, un cuerpo vacío: la API usa los últimos 7 días.
export function reportBody(dates: ReportDates): { start_date?: string; end_date?: string } {
  const body: { start_date?: string; end_date?: string } = {};
  if (dates.from) body.start_date = dates.from;
  if (dates.to) body.end_date = nextDay(dates.to);
  return body;
}

// Texto de la carga según el estado de la tarea: encolando, en cola o calculando.
export function progressLabel(progress: ReportProgress | null): string {
  if (progress === "pending") return "En cola: el reporte se calculará en cuanto haya un worker libre...";
  if (progress === "started") return "Calculando el reporte...";
  return "Pidiendo el reporte...";
}

// Espera entre consultas: cada 1 s los primeros 10 s y después cada 2 s.
export function pollDelay(elapsedMs: number): number {
  return elapsedMs < POLL_FAST_PHASE_MS ? POLL_FAST_MS : POLL_SLOW_MS;
}

// Mensaje de una tarea fallida: el error que devuelve la API (tipo y primera línea, sin SQL).
export function reportFailedMessage(result: unknown): string {
  const error =
    result && typeof result === "object" && "error" in result && typeof result.error === "string" ? result.error : null;
  const detail = error ? ` (${error})` : "";
  return `No se pudo calcular el reporte técnico${detail}. Vuelve a intentarlo; si continúa, avisa al equipo técnico.`;
}

// Espera `ms`, o menos si se cancela: entonces la siguiente comprobación lanza el AbortError.
function sleep(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve) => {
    const timer = setTimeout(done, ms);
    function done() {
      clearTimeout(timer);
      signal?.removeEventListener("abort", done);
      resolve();
    }
    signal?.addEventListener("abort", done, { once: true });
  });
}

export interface ReportPollingOptions {
  // Cada estado intermedio que se observa (`pending` o `started`).
  onProgress?: (progress: ReportProgress) => void;
  // Cancela el sondeo al cambiar las fechas o salir de la vista. La petición en curso termina, pero su
  // respuesta se descarta y no se hace ninguna más.
  signal?: AbortSignal;
  // Para las pruebas: la espera y el reloj.
  wait?: (ms: number, signal?: AbortSignal) => Promise<void>;
  now?: () => number;
}

async function enqueueReport(dates: ReportDates): Promise<string> {
  try {
    const { task_id } = await apiJson<TaskAccepted>(REPORT_PATH, {
      ...jsonBody("POST", reportBody(dates)),
      fallback: "no se pudo pedir el reporte técnico",
    });
    return task_id;
  } catch (error) {
    // 403: la sesión es válida pero el rol no es admin. No cierra la sesión (lo decide api-client).
    if (error instanceof ApiError && error.status === 403 && error.code !== "inactive_user") {
      throw new ApiError(ADMIN_ONLY_MESSAGE, 403, error.code, [], error.requestId);
    }
    throw error;
  }
}

// Encola el reporte y espera su resultado consultando el estado de la tarea.
export async function getTelemetryReport(dates: ReportDates, options: ReportPollingOptions = {}): Promise<TelemetryReport> {
  const { onProgress, signal, wait = sleep, now = Date.now } = options;
  signal?.throwIfAborted();
  const taskId = await enqueueReport(dates);
  const startedAt = now();

  for (;;) {
    signal?.throwIfAborted();
    const task = await apiJson<TaskStatus<TelemetryReport>>(`${TASKS_PATH}/${encodeURIComponent(taskId)}`, {
      fallback: "no se pudo consultar el estado del reporte técnico",
    });
    signal?.throwIfAborted();

    if (task.status === "success") return task.result as TelemetryReport;
    if (task.status === "failure") throw new ApiError(reportFailedMessage(task.result), 0, "report_failed");

    onProgress?.(task.status);
    const elapsed = now() - startedAt;
    if (elapsed >= POLL_TIMEOUT_MS) throw new ApiError(SLOW_REPORT_MESSAGE, 0, "report_timeout");
    await wait(pollDelay(elapsed), signal);
  }
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
