// Configuración del servicio de telemetría (plan de telemetría, sección 13).
//
// Las variables NEXT_PUBLIC_ se sustituyen por su valor al compilar: por eso se leen con su nombre
// completo (`process.env.NEXT_PUBLIC_…`), nunca con un acceso dinámico.

export type TelemetryEnvironment = "development" | "staging" | "production";

const ENVIRONMENTS: readonly TelemetryEnvironment[] = ["development", "staging", "production"];

// URL del receptor. Hoy, el stub POST /telemetry/events de la API; en la fase de almacenamiento, el
// receptor real. El código no cambia: solo esta variable. Sin ella, la telemetría está desactivada.
export const TELEMETRY_ENDPOINT: string | null = process.env.NEXT_PUBLIC_TELEMETRY_ENDPOINT?.trim() || null;

// Entorno de los eventos (`environment` del envelope), para no mezclar datos de prueba con los reales.
export const TELEMETRY_ENVIRONMENT: TelemetryEnvironment = parseEnvironment(process.env.NEXT_PUBLIC_TELEMETRY_ENVIRONMENT);

export function parseEnvironment(value: string | undefined): TelemetryEnvironment {
  const normalized = value?.trim().toLowerCase();
  return ENVIRONMENTS.find((environment) => environment === normalized) ?? "development";
}

// Envío (decisión C7 y enunciado): un lote cada 10 s o al llegar a 20 eventos, lo que ocurra primero.
export const BATCH_SIZE = 20;
export const FLUSH_INTERVAL_MS = 10_000;
// Hasta 3 reintentos con espera exponencial; después se descarta el lote.
export const RETRY_DELAYS_MS: readonly number[] = [1_000, 2_000, 4_000];
// Si el receptor no responde durante mucho tiempo, la cola no crece sin límite: se descartan los más antiguos.
export const MAX_QUEUE_SIZE = 500;
// sendBeacon admite unos 64 KB por envío: los pendientes salen en lotes pequeños.
export const BEACON_BATCH_SIZE = 20;

export const IS_DEVELOPMENT = process.env.NODE_ENV !== "production";
