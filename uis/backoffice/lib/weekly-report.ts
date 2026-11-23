import { ApiError, apiJson } from "@/lib/api-client";
import type {
  Country,
  Currency,
  KpiKey,
  LocationWeekPerformance,
  PipelineRun,
  WeeklyLocationPerformance,
  WeeklyReportResult,
} from "@/types/weekly-report";

// Reporte Semanal de Costo y Merma por Local (briefing del pipeline de desempeño de negocio): la vista
// /reporte-semanal lo pide aquí y lo muestra a la dirección. Las rutas son las del intermediario
// (app/api/reporting/), que las reenvía a /reporting de la API, fuera de /api/v1. No calcula KPIs
// propios: solo da formato a los de reporting.weekly_location_performance, salvo el resumen por país,
// que suma los locales de un mismo país (misma moneda).

const WEEKLY_PATH = "/reporting/weekly-location-performance";
const LATEST_RUN_PATH = "/reporting/pipeline-runs/latest";

export const READERS_ONLY_MESSAGE = "Solo los administradores y los gerentes pueden ver el reporte semanal.";

const DAY_MS = 24 * 60 * 60 * 1000;
// Si la última corrida correcta tiene más días que estos, se saltó al menos un lunes.
export const STALE_AFTER_DAYS = 8;

// 403: la sesión es válida pero el rol no puede leer el reporte. No cierra la sesión (lo decide api-client).
function readersOnly(error: unknown): unknown {
  if (error instanceof ApiError && error.status === 403 && error.code !== "inactive_user") {
    return new ApiError(READERS_ONLY_MESSAGE, 403, error.code, [], error.requestId);
  }
  return error;
}

// Los KPIs de una semana (`weekStart`, un lunes YYYY-MM-DD) o, sin ella, de la última calculada.
// Una semana sin calcular no es un error para la vista: se muestra como tal.
export async function getWeeklyReport(weekStart: string | null): Promise<WeeklyReportResult> {
  const query = weekStart ? `?week_start=${encodeURIComponent(weekStart)}` : "";
  try {
    const report = await apiJson<WeeklyLocationPerformance>(`${WEEKLY_PATH}${query}`, {
      fallback: "no se pudo cargar el reporte semanal",
    });
    return { status: "computed", report };
  } catch (error) {
    if (error instanceof ApiError && error.status === 404 && error.code === "week_not_computed") {
      return { status: "not_computed", weekStart };
    }
    throw readersOnly(error);
  }
}

// La última corrida del pipeline, o null si nunca corrió.
export async function getLatestPipelineRun(): Promise<PipelineRun | null> {
  try {
    return await apiJson<PipelineRun>(LATEST_RUN_PATH, { fallback: "no se pudo consultar la última actualización" });
  } catch (error) {
    if (error instanceof ApiError && error.status === 404 && error.code === "no_pipeline_runs") return null;
    throw readersOnly(error);
  }
}

// --- KPIs del briefing ("KPIs a medir") --------------------------------------------------------------

export type KpiKind = "money" | "ratio" | "count";

export interface KpiDefinition {
  key: KpiKey;
  // El nombre del KPI tal como aparece en el briefing.
  label: string;
  // "Qué mide", del briefing.
  measures: string;
  kind: KpiKind;
}

export const KPIS: KpiDefinition[] = [
  {
    key: "total_purchase_cost",
    label: "Costo de compra por local",
    measures: "Cuánto gastó un local comprando ingredientes a proveedores durante la semana.",
    kind: "money",
  },
  {
    key: "total_waste_cost",
    label: "Costo de merma por local",
    measures:
      "Cuánto perdió un local por producto vencido, error de cocina o robo durante la semana, en términos monetarios.",
    kind: "money",
  },
  {
    key: "waste_ratio",
    label: "Ratio de merma",
    measures: "El costo de merma como proporción del costo de compra, para ese local y esa semana.",
    kind: "ratio",
  },
  {
    key: "stockout_events_count",
    label: "Frecuencia de quiebre de stock",
    measures:
      "Cuántas veces durante la semana el stock de algún ingrediente en un local cayó por debajo del mínimo configurado.",
    kind: "count",
  },
  {
    key: "price_alert_events_count",
    label: "Frecuencia de alertas de precio",
    measures: "Cuántas veces durante la semana el costo de un ingrediente subió de forma anómala respecto a su histórico.",
    kind: "count",
  },
];

export const COUNTRIES: { country: Country; label: string; currency: Currency }[] = [
  { country: "CO", label: "Colombia", currency: "COP" },
  { country: "US", label: "Estados Unidos", currency: "USD" },
];

// --- Formato ------------------------------------------------------------------------------------------

const LOCALE = "es-CO";

// Importe en la moneda del local, sin convertir. Ej.: "$ 1.530.000" (COP), "US$ 100,00" (USD).
// Los pesos se muestran sin decimales salvo que los tengan (106,25).
export function formatMoney(value: number, currency: Currency): string {
  const decimals = currency === "COP" ? { minimumFractionDigits: 0, maximumFractionDigits: 2 } : { minimumFractionDigits: 2, maximumFractionDigits: 2 };
  return new Intl.NumberFormat(LOCALE, { style: "currency", currency, ...decimals }).format(value);
}

// Ratio como porcentaje con hasta un decimal. Ej.: 0.125 → "12,5 %"; 3 → "300 %".
export function formatRatio(ratio: number): string {
  const percent = new Intl.NumberFormat(LOCALE, { maximumFractionDigits: 1 }).format(ratio * 100);
  return `${percent} %`;
}

export function formatCount(value: number): string {
  return new Intl.NumberFormat(LOCALE, { maximumFractionDigits: 0 }).format(value);
}

export function formatKpi(kind: KpiKind, value: number, currency: Currency): string {
  if (kind === "money") return formatMoney(value, currency);
  if (kind === "ratio") return formatRatio(value);
  return formatCount(value);
}

// --- Semanas ------------------------------------------------------------------------------------------

const MONTHS = [
  "enero", "febrero", "marzo", "abril", "mayo", "junio",
  "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
];

function parseDay(day: string): Date {
  return new Date(`${day}T00:00:00Z`);
}

function toDay(date: Date): string {
  return date.toISOString().slice(0, 10);
}

// El lunes `weeks` semanas antes (negativo) o después (positivo). Ej.: shiftWeek("2026-11-16", -1) → "2026-11-09".
export function shiftWeek(weekStart: string, weeks: number): string {
  return toDay(new Date(parseDay(weekStart).getTime() + weeks * 7 * DAY_MS));
}

// Lunes (UTC) de la semana que contiene `now`.
export function currentWeekStart(now: Date): string {
  const today = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate());
  const weekday = (new Date(today).getUTCDay() + 6) % 7; // lunes = 0
  return toDay(new Date(today - weekday * DAY_MS));
}

// La semana aún no ha terminado (domingo 23:59 UTC): sus datos son parciales.
export function isCurrentWeek(weekStart: string, now: Date): boolean {
  return weekStart >= currentWeekStart(now);
}

// El período en palabras. Ej.: "Semana del lunes 16 al domingo 22 de noviembre de 2026";
// "Semana del lunes 30 de noviembre al domingo 6 de diciembre de 2026".
export function formatWeekPeriod(weekStart: string): string {
  const start = parseDay(weekStart);
  const end = new Date(start.getTime() + 6 * DAY_MS);
  const [startDay, startMonth, startYear] = [start.getUTCDate(), start.getUTCMonth(), start.getUTCFullYear()];
  const [endDay, endMonth, endYear] = [end.getUTCDate(), end.getUTCMonth(), end.getUTCFullYear()];
  const endText = `${endDay} de ${MONTHS[endMonth]} de ${endYear}`;
  if (startYear !== endYear) {
    return `Semana del lunes ${startDay} de ${MONTHS[startMonth]} de ${startYear} al domingo ${endText}`;
  }
  if (startMonth !== endMonth) {
    return `Semana del lunes ${startDay} de ${MONTHS[startMonth]} al domingo ${endText}`;
  }
  return `Semana del lunes ${startDay} al domingo ${endText}`;
}

// --- Datos de la vista --------------------------------------------------------------------------------

export function locationsOf(report: WeeklyLocationPerformance, country: Country): LocationWeekPerformance[] {
  return report.locations.filter((location) => location.country === country);
}

// Locales de un país de mayor a menor en un KPI; a igual valor, por nombre.
export function rankBy(locations: LocationWeekPerformance[], key: KpiKey): LocationWeekPerformance[] {
  return [...locations].sort((a, b) => b[key] - a[key] || a.location_name.localeCompare(b.location_name, "es"));
}

export interface CountrySummary {
  country: Country;
  label: string;
  currency: Currency;
  locations: number;
  total_purchase_cost: number;
  total_waste_cost: number;
  // Merma del país sobre sus compras (no la media de los ratios de sus locales); 0 sin compras.
  waste_ratio: number;
  stockout_events_count: number;
  price_alert_events_count: number;
}

// Consolidado por país: suma los locales de un mismo país, que comparten moneda. Nunca suma COP con USD.
export function summarizeByCountry(report: WeeklyLocationPerformance): CountrySummary[] {
  return COUNTRIES.map(({ country, label, currency }) => {
    const rows = locationsOf(report, country);
    const sum = (key: KpiKey) => rows.reduce((total, row) => total + row[key], 0);
    const purchase = sum("total_purchase_cost");
    const waste = sum("total_waste_cost");
    return {
      country,
      label,
      currency,
      locations: rows.length,
      total_purchase_cost: Math.round(purchase * 100) / 100,
      total_waste_cost: Math.round(waste * 100) / 100,
      waste_ratio: purchase > 0 ? Math.round((waste / purchase) * 10000) / 10000 : 0,
      stockout_events_count: sum("stockout_events_count"),
      price_alert_events_count: sum("price_alert_events_count"),
    };
  }).filter((summary) => summary.locations > 0);
}

// Ancho (en %) de una barra respecto al mayor valor de su grupo; 0 si no hay mayor.
export function barPercent(value: number, max: number): number {
  if (max <= 0 || value <= 0) return 0;
  return Math.min(100, (value / max) * 100);
}

// Ningún local tuvo actividad en la semana: puede ser una semana real sin compras ni mermas
// registradas, o un fallo en la captura de datos (señal de silencio, diseño §12).
export function isSilentWeek(report: WeeklyLocationPerformance): boolean {
  return report.locations.every((location) =>
    KPIS.every(({ key }) => location[key] === 0),
  );
}

// --- Actualización ------------------------------------------------------------------------------------

export type Freshness =
  | { status: "unknown" }
  | { status: "never" }
  | { status: "updating"; since: string }
  | { status: "failed"; at: string }
  | { status: "stale"; at: string }
  | { status: "fresh"; at: string };

// Qué decir sobre la actualización de los datos a partir de la última corrida del pipeline.
// - "stale": la última corrida terminó bien pero hace más de STALE_AFTER_DAYS días (se saltó un lunes).
export function freshnessOf(run: PipelineRun | null | undefined, now: Date): Freshness {
  if (run === undefined) return { status: "unknown" };
  if (run === null) return { status: "never" };
  if (run.status === "pending" || run.status === "running") return { status: "updating", since: run.created_at };
  const at = run.finished_at ?? run.created_at;
  if (run.status === "failed") return { status: "failed", at };
  const ageDays = (now.getTime() - Date.parse(at)) / DAY_MS;
  return ageDays > STALE_AFTER_DAYS ? { status: "stale", at } : { status: "fresh", at };
}
