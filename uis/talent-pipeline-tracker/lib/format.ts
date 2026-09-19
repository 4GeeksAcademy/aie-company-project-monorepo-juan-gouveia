const LOCALE = "es";

// Ej.: "18 de septiembre de 2026"
export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(LOCALE, {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

// Ej.: "18 sept 2026, 14:30"
export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString(LOCALE, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}
