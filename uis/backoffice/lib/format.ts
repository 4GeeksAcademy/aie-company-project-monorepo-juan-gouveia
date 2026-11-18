const LOCALE = "es";

// Lo que se muestra cuando falta un dato o no se puede formatear.
const MISSING = "—";

// Las fechas llegan de las APIs como texto ISO. Si faltan o no se pueden leer, se devuelve null para
// mostrar "—" en lugar de "Invalid Date". `new Date(null)` daría 1970, por eso se comprueba antes.
function parseDate(iso: string | null | undefined): Date | null {
  if (!iso) return null;
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? null : date;
}

// Ej.: "18 de septiembre de 2026"; "—" si la fecha falta o no es válida.
export function formatDate(iso: string | null | undefined): string {
  const date = parseDate(iso);
  if (!date) return MISSING;
  return date.toLocaleDateString(LOCALE, {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

// Las métricas usan punto decimal, como el reporte de Operaciones y el CSV exportado.
// Ej.: "30.2%"; "—" si no hay porcentaje (total en 0).
export function formatPercentage(value: number | null): string {
  return value === null ? MISSING : `${value.toFixed(1)}%`;
}

// Ej.: "3.46"
export function formatDecimal(value: number, digits = 2): string {
  return value.toFixed(digits);
}

// Ej.: "18 sept 2026, 14:30"; "—" si la fecha falta o no es válida.
export function formatDateTime(iso: string | null | undefined): string {
  const date = parseDate(iso);
  if (!date) return MISSING;
  return date.toLocaleString(LOCALE, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

// Fecha y hora en UTC, con la zona explícita. Ej.: "14 ene 2024, 0:00 UTC".
// La usa el gestor de incidencias: el histórico se cargó como medianoche UTC (briefing), y en hora
// local de Colombia o Florida se vería como el día anterior. "—" si la fecha falta o no es válida.
export function formatDateTimeUtc(iso: string | null | undefined): string {
  const date = parseDate(iso);
  if (!date) return MISSING;
  const text = date.toLocaleString(LOCALE, {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  });
  return `${text} UTC`;
}
