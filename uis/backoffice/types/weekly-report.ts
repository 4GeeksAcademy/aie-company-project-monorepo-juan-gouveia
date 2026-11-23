// Respuestas de los endpoints del Reporte Semanal de Costo y Merma por Local (services/reporting).

export type Country = "CO" | "US";
export type Currency = "COP" | "USD";

// Una fila de GET /reporting/weekly-location-performance: los cinco KPIs de un local en una semana, en la
// moneda del local. `waste_ratio` es una fracción (0,125 = 12,5 %) y puede superar 1.
export interface LocationWeekPerformance {
  location_id: string;
  location_name: string;
  country: Country;
  total_purchase_cost: number;
  total_waste_cost: number;
  waste_ratio: number;
  stockout_events_count: number;
  price_alert_events_count: number;
  currency: Currency;
}

// GET /reporting/weekly-location-performance: los 14 locales de una semana ISO (`week_start`, el lunes).
export interface WeeklyLocationPerformance {
  week_start: string;
  locations: LocationWeekPerformance[];
}

export type PipelineRunStatus = "pending" | "running" | "completed" | "failed";

// GET /reporting/pipeline-runs/latest: la última corrida del pipeline que calcula el reporte.
export interface PipelineRun {
  id: string;
  pipeline: string;
  trigger: "scheduled" | "manual";
  status: PipelineRunStatus;
  week_from: string;
  week_to: string;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  events_read: number;
  events_rejected: number;
  events_discarded: number;
  waste_events_without_cost: number;
  issues: Record<string, number>;
  rows_written: number;
  failed_task: string | null;
  error_message: string | null;
}

// Lo que muestra la vista para una semana: el reporte, o que esa semana no está calculada.
export type WeeklyReportResult =
  | { status: "computed"; report: WeeklyLocationPerformance }
  | { status: "not_computed"; weekStart: string | null };

// Las cinco columnas de KPI de la tabla de destino.
export type KpiKey =
  | "total_purchase_cost"
  | "total_waste_cost"
  | "waste_ratio"
  | "stockout_events_count"
  | "price_alert_events_count";
