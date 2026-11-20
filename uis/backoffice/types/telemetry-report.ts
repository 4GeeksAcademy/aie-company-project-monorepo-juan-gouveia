// Respuesta de GET /telemetry/report (plan de telemetría, sección 16). Todas las filas son de un día UTC
// (`date`, YYYY-MM-DD) y las tasas son fracciones de 0 a 1.

export type ReportLevel = "info" | "warn" | "error";

export interface EventsPerDay {
  date: string;
  total: number;
  info: number;
  warn: number;
  error: number;
}

export interface ErrorRateByType {
  date: string;
  event_type: string;
  level: "warn" | "error";
  count: number;
  rate: number;
}

export interface ApiLatencyByRoute {
  date: string;
  method: string;
  route: string;
  samples: number;
  avg_ms: number;
  max_ms: number;
}

export interface AuthFailureRate {
  date: string;
  attempts: number;
  failed: number;
  failure_rate: number;
}

export interface TelemetryReport {
  // Ventana [from, to) en UTC: inicio inclusivo, fin exclusivo.
  period: { from: string; to: string };
  metrics: {
    events_per_day: EventsPerDay[];
    error_rate_by_type: ErrorRateByType[];
    api_latency_by_route: ApiLatencyByRoute[];
    auth_failure_rate: AuthFailureRate[];
  };
}

// Fechas elegidas en la vista (YYYY-MM-DD, ambas incluidas); vacías = los últimos 7 días.
export interface ReportDates {
  from: string;
  to: string;
}
