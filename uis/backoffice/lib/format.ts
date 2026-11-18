const LOCALE = "es";

// Ej.: "18 de septiembre de 2026"
export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(LOCALE, {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

// Las métricas usan punto decimal, como el reporte de Operaciones y el CSV exportado.
// Ej.: "30.2%"; "—" si no hay porcentaje (total en 0).
export function formatPercentage(value: number | null): string {
  return value === null ? "—" : `${value.toFixed(1)}%`;
}

// Ej.: "3.46"
export function formatDecimal(value: number, digits = 2): string {
  return value.toFixed(digits);
}

// Ej.: "18 sept 2026, 14:30"
export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString(LOCALE, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

// Fecha y hora en UTC, con la zona explícita. Ej.: "14 ene 2024, 0:00 UTC".
// La usa el gestor de incidencias: el histórico se cargó como medianoche UTC (briefing), y en hora
// local de Colombia o Florida se vería como el día anterior.
export function formatDateTimeUtc(iso: string): string {
  const text = new Date(iso).toLocaleString(LOCALE, {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  });
  return `${text} UTC`;
}
