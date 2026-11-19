import {
  BATCH_SIZE,
  BEACON_BATCH_SIZE,
  FLUSH_INTERVAL_MS,
  IS_DEVELOPMENT,
  MAX_QUEUE_SIZE,
  RETRY_DELAYS_MS,
  TELEMETRY_ENDPOINT,
  TELEMETRY_ENVIRONMENT,
} from "@/lib/telemetry/config";
import { buildEnvelope } from "@/lib/telemetry/envelope";
import { createTelemetryQueue, type TelemetryQueue } from "@/lib/telemetry/queue";
import { compactProperties, validateEvent } from "@/lib/telemetry/validate";

// TelemetryService del backoffice (plan de telemetría, sección 13).
//
// Su única función pública es track(): todo el tracking del backoffice pasa por aquí, nunca por fetch
// directos. Quien llama solo indica el tipo de evento y sus propiedades. El servicio:
// 1. comprueba el evento contra el catálogo generado desde event-schemas.json (tipo, obligatorias y
//    allowlist) y lo descarta si no cumple;
// 2. le añade el envelope: eventId, timestamp de la captura, sessionId, userId, schemaVersion del
//    esquema de ese evento, requestId de la llamada a la API que lo originó, source y environment;
// 3. lo deja en la cola, que lo envía por lotes a NEXT_PUBLIC_TELEMETRY_ENDPOINT.
//
// Nunca lanza errores ni bloquea: la telemetría no es crítica. En el servidor (render de Next) y sin
// NEXT_PUBLIC_TELEMETRY_ENDPOINT no hace nada.

let queue: TelemetryQueue | null = null;
let warnedDisabled = false;

function warn(message: string) {
  if (IS_DEVELOPMENT) console.warn(`[telemetría] ${message}`);
}

function getQueue(endpoint: string): TelemetryQueue {
  if (queue) return queue;
  const created = createTelemetryQueue({
    endpoint,
    batchSize: BATCH_SIZE,
    flushIntervalMs: FLUSH_INTERVAL_MS,
    retryDelaysMs: RETRY_DELAYS_MS,
    maxQueueSize: MAX_QUEUE_SIZE,
    beaconBatchSize: BEACON_BATCH_SIZE,
    fetch: (...args) => window.fetch(...args),
    sendBeacon: typeof navigator.sendBeacon === "function" ? (url, data) => navigator.sendBeacon(url, data) : undefined,
    onDiscard: (count, reason) => warn(`${count} evento(s) descartado(s): ${reason}.`),
  });
  // Al ocultar o cerrar la pestaña, el navegador cancela las peticiones en curso: lo pendiente sale
  // con sendBeacon. pagehide cubre los navegadores que no emiten visibilitychange al cerrar.
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") created.flushWithBeacon();
  });
  window.addEventListener("pagehide", () => created.flushWithBeacon());
  queue = created;
  return created;
}

export function track(eventType: string, properties: Record<string, unknown>): void {
  if (typeof window === "undefined") return;
  try {
    const result = validateEvent(eventType, properties);
    if (!result.ok) {
      warn(`evento descartado: ${result.reason}.`);
      return;
    }
    if (!TELEMETRY_ENDPOINT) {
      if (!warnedDisabled) warn("desactivada: falta NEXT_PUBLIC_TELEMETRY_ENDPOINT.");
      warnedDisabled = true;
      return;
    }
    const envelope = buildEnvelope(eventType, compactProperties(properties), result.entry.version, TELEMETRY_ENVIRONMENT);
    getQueue(TELEMETRY_ENDPOINT).enqueue(envelope);
  } catch (error) {
    warn(`error inesperado al capturar ${eventType}: ${error instanceof Error ? error.message : String(error)}`);
  }
}
