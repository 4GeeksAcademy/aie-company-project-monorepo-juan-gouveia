import type { TelemetryEnvironment } from "@/lib/telemetry/config";
import { uuidV4 } from "@/lib/telemetry/ids";
import { currentRequestId } from "@/lib/telemetry/request-context";
import { currentSession } from "@/lib/telemetry/session";

// Event Envelope del plan (sección 7): los 8 campos del enunciado, más `source` y `environment`.
// Lo construye el servicio; quien llama a track() solo aporta `event_type` y `properties`.
export interface TelemetryEnvelope {
  eventId: string;
  timestamp: string;
  sessionId: string | null;
  userId: string | null;
  event_type: string;
  schemaVersion: string;
  requestId: string | null;
  properties: Record<string, unknown>;
  source: "browser";
  environment: TelemetryEnvironment;
}

export function buildEnvelope(
  eventType: string,
  properties: Record<string, unknown>,
  schemaVersion: string,
  environment: TelemetryEnvironment,
  now: Date = new Date()
): TelemetryEnvelope {
  const session = currentSession(now.getTime());
  return {
    eventId: uuidV4(),
    // Momento de la captura, no del envío; toISOString da UTC con milisegundos (…:46.123Z).
    timestamp: now.toISOString(),
    sessionId: session.sessionId,
    userId: session.userId,
    event_type: eventType,
    schemaVersion,
    requestId: currentRequestId(),
    properties,
    source: "browser",
    environment,
  };
}
