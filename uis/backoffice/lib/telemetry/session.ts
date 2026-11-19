import { getToken, readTokenClaims } from "@/lib/auth/token";
import { uuidV4 } from "@/lib/telemetry/ids";

// Sesión de telemetría (`sessionId` y `userId` del envelope; decisión C6).
//
// - `sessionId` nace al iniciar sesión y vive en sessionStorage: sobrevive a una recarga (F5) pero
//   es propio de cada pestaña. Una pestaña nueva con la sesión ya iniciada crea el suyo.
// - Sin token (vistas públicas, sesión cerrada o caducada) no hay sesión: `sessionId` es null y el
//   guardado se borra, así que el siguiente login empieza una sesión nueva.
// - Si el token es de otra cuenta, también empieza una sesión nueva.
// - `userId` es el `sub` del token: el UUID de la cuenta, nunca el email ni el nombre.
//
// No hace falta llamar a nada al iniciar o cerrar sesión: se deduce del token en cada evento.

const SESSION_KEY = "brasaland.telemetry_session";

interface StoredSession {
  id: string;
  sub: string;
  startedAt: number;
}

export interface TelemetrySession {
  sessionId: string | null;
  userId: string | null;
  // Momento de inicio (ms), para medir la duración de la sesión al cerrarla.
  startedAt: number | null;
}

const NO_SESSION: TelemetrySession = { sessionId: null, userId: null, startedAt: null };

function storage(): Storage | null {
  try {
    return typeof window === "undefined" ? null : window.sessionStorage;
  } catch {
    return null;
  }
}

function readStored(store: Storage | null): StoredSession | null {
  try {
    const raw = store?.getItem(SESSION_KEY);
    if (!raw) return null;
    const value = JSON.parse(raw) as Partial<StoredSession>;
    if (typeof value.id !== "string" || typeof value.sub !== "string" || typeof value.startedAt !== "number") return null;
    return value as StoredSession;
  } catch {
    return null;
  }
}

function write(store: Storage | null, session: StoredSession | null): void {
  try {
    if (session) store?.setItem(SESSION_KEY, JSON.stringify(session));
    else store?.removeItem(SESSION_KEY);
  } catch {
    // sessionStorage bloqueado: la sesión dura lo que dure la página. La telemetría no falla por ello.
  }
}

// Sesión del momento, creada o descartada según el token.
export function currentSession(now: number = Date.now()): TelemetrySession {
  const claims = readTokenClaims(getToken());
  const store = storage();
  if (!claims) {
    write(store, null);
    return NO_SESSION;
  }

  let stored = readStored(store);
  if (!stored || stored.sub !== claims.sub) {
    stored = { id: uuidV4(), sub: claims.sub, startedAt: now };
    write(store, stored);
  }
  return { sessionId: stored.id, userId: claims.sub, startedAt: stored.startedAt };
}
