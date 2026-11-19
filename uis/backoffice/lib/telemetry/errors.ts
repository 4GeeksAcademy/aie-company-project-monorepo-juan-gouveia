import { track } from "@/lib/telemetry";
import { pageRouteTemplate } from "@/lib/telemetry/routes";

// `frontend_error_captured` (plan, §5.5): errores de JavaScript que nadie reporta. Se capturan en tres
// sitios: window.onerror, unhandledrejection (components/telemetry/TelemetryRoot.tsx) y las pantallas
// de error de Next (`error.tsx` y `global-error.tsx`).
//
// Datos sensibles (§8.2): el mensaje se recorta a 200 caracteres y se le sustituyen los emails, los
// números de 4 o más cifras y los UUID por `[redacted]`. Nunca se envía la pila completa.
//
// Throttle (§10): una vez por huella cada 60 s, y como máximo 20 por sesión de la página, para que un
// error en bucle no inunde la telemetría.

export type ErrorSource = "window_error" | "unhandled_rejection" | "error_boundary";

const MAX_MESSAGE_LENGTH = 200;
const MAX_NAME_LENGTH = 60;
const REPEAT_WINDOW_MS = 60_000;
const MAX_PER_PAGE = 20;

const lastSeen = new Map<string, number>();
let sentThisPage = 0;

export function sanitizeMessage(message: string): string {
  return message
    .replace(/[^\s@]+@[^\s@]+\.[^\s@]+/g, "[redacted]")
    .replace(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/gi, "[redacted]")
    .replace(/\d{4,}/g, "[redacted]")
    .slice(0, MAX_MESSAGE_LENGTH);
}

// Primer marco de la pila, sin números de línea ni columna: el mismo fallo en otra compilación
// conserva su huella.
function firstFrame(stack: string | undefined): string {
  const frame = stack?.split("\n").find((line) => /\bat\b|@/.test(line)) ?? "";
  return frame.replace(/:\d+(:\d+)?/g, "").replace(/\?[^)\s]*/g, "").trim();
}

// FNV-1a de 64 bits en hexadecimal (16 caracteres), sobre las unidades UTF-16 del texto. Es síncrono
// y existe en cualquier página; crypto.subtle (SHA-256) solo existe con HTTPS o en localhost, y la
// huella debe ser la misma en todas.
export function fingerprint(text: string): string {
  let hash = BigInt("0xcbf29ce484222325");
  const prime = BigInt("0x100000001b3");
  const mask = BigInt("0xffffffffffffffff");
  for (let index = 0; index < text.length; index++) {
    hash = ((hash ^ BigInt(text.charCodeAt(index))) * prime) & mask;
  }
  return hash.toString(16).padStart(16, "0");
}

function describe(error: unknown): { name: string; message: string; stack: string | undefined } {
  if (error instanceof Error) return { name: error.name || "Error", message: error.message, stack: error.stack };
  if (typeof error === "string") return { name: "Error", message: error, stack: undefined };
  return { name: "NonError", message: "Valor lanzado que no es un Error", stack: undefined };
}

export function captureFrontendError(error: unknown, source: ErrorSource, now: number = Date.now()): void {
  try {
    const { name, message, stack } = describe(error);
    const errorFingerprint = fingerprint(`${name}|${firstFrame(stack) || message}`);
    const previous = lastSeen.get(errorFingerprint);
    if (sentThisPage >= MAX_PER_PAGE || (previous !== undefined && now - previous < REPEAT_WINDOW_MS)) return;
    lastSeen.set(errorFingerprint, now);
    sentThisPage++;
    track("frontend_error_captured", {
      route: pageRouteTemplate(window.location.pathname),
      error_name: name.slice(0, MAX_NAME_LENGTH),
      message_sanitized: sanitizeMessage(message) || "(sin mensaje)",
      error_fingerprint: errorFingerprint,
      source,
    });
  } catch {
    // Capturar un error nunca debe provocar otro.
  }
}

// Solo para las pruebas.
export function resetErrorThrottle(): void {
  lastSeen.clear();
  sentThisPage = 0;
}
