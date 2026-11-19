import type { TelemetryEnvelope } from "@/lib/telemetry/envelope";

// Cola local y envío por lotes (plan, sección 13.2):
// - los eventos se acumulan en memoria y salen en lotes `{"events": [...]}`: al llegar a `batchSize`
//   o cuando pasan `flushIntervalMs` desde el primer evento pendiente, lo que ocurra primero;
// - un lote que falla se reintenta con las esperas de `retryDelaysMs` y después se descarta: la
//   telemetría nunca bloquea la aplicación. Los reintentos conservan los `eventId`;
// - al ocultarse o cerrarse la pestaña, flushWithBeacon() envía lo pendiente con sendBeacon, también
//   el lote que esperaba un reintento.
//
// Las dependencias del navegador (fetch, sendBeacon, temporizadores) se inyectan para poder probarla.

export interface TelemetryQueueOptions {
  endpoint: string;
  batchSize: number;
  flushIntervalMs: number;
  retryDelaysMs: readonly number[];
  maxQueueSize: number;
  beaconBatchSize: number;
  fetch: typeof fetch;
  sendBeacon?: (url: string, data: Blob) => boolean;
  schedule?: (callback: () => void, ms: number) => unknown;
  cancel?: (handle: unknown) => void;
  // Avisa de los eventos descartados (para el log de desarrollo).
  onDiscard?: (count: number, reason: string) => void;
}

export interface TelemetryQueue {
  enqueue(event: TelemetryEnvelope): void;
  flush(): void;
  flushWithBeacon(): void;
  size(): number;
}

interface InFlight {
  events: TelemetryEnvelope[];
  // El lote se entregó con sendBeacon mientras esperaba un reintento: no hay que seguir reintentando.
  handedOff: boolean;
}

// 408 (timeout) y 429 (demasiadas peticiones) pueden salir bien más tarde; el resto de 4xx no.
function isRetryable(status: number): boolean {
  return status >= 500 || status === 408 || status === 429;
}

export function createTelemetryQueue(options: TelemetryQueueOptions): TelemetryQueue {
  const schedule = options.schedule ?? ((callback, ms) => setTimeout(callback, ms));
  const cancel = options.cancel ?? ((handle) => clearTimeout(handle as ReturnType<typeof setTimeout>));
  const discard = (count: number, reason: string) => {
    if (count > 0) options.onDiscard?.(count, reason);
  };

  let queue: TelemetryEnvelope[] = [];
  let timer: unknown = null;
  let inFlight: InFlight | null = null;

  function wait(ms: number): Promise<void> {
    return new Promise((resolve) => schedule(resolve, ms));
  }

  function scheduleFlush() {
    if (timer === null && queue.length > 0) timer = schedule(flush, options.flushIntervalMs);
  }

  function clearTimer() {
    if (timer !== null) cancel(timer);
    timer = null;
  }

  async function post(events: TelemetryEnvelope[]): Promise<number> {
    const response = await options.fetch(options.endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ events }),
      // Sin cookies ni credenciales: el receptor es público y está en otro origen.
      credentials: "omit",
    });
    return response.status;
  }

  async function send(batch: InFlight) {
    for (let attempt = 0; ; attempt++) {
      let status: number | null = null;
      try {
        status = await post(batch.events);
      } catch {
        // Error de red: se reintenta.
      }
      if (batch.handedOff) return;
      if (status !== null && status >= 200 && status < 300) return;
      if (status !== null && !isRetryable(status)) {
        discard(batch.events.length, `el receptor rechazó el lote (${status})`);
        return;
      }
      if (attempt >= options.retryDelaysMs.length) {
        discard(batch.events.length, `el envío falló tras ${options.retryDelaysMs.length} reintentos`);
        return;
      }
      await wait(options.retryDelaysMs[attempt]);
      if (batch.handedOff) return;
    }
  }

  function flush() {
    clearTimer();
    if (inFlight || queue.length === 0) return;
    const batch: InFlight = { events: queue.splice(0, options.batchSize), handedOff: false };
    inFlight = batch;
    void send(batch).finally(() => {
      if (inFlight === batch) inFlight = null;
      // Lo que llegó mientras tanto: otro lote si ya hay suficientes; si no, el temporizador.
      if (queue.length >= options.batchSize) flush();
      else scheduleFlush();
    });
  }

  function enqueue(event: TelemetryEnvelope) {
    queue.push(event);
    if (queue.length > options.maxQueueSize) {
      const overflow = queue.length - options.maxQueueSize;
      queue = queue.slice(overflow);
      discard(overflow, "la cola superó su tamaño máximo (se descartan los más antiguos)");
    }
    if (queue.length >= options.batchSize) flush();
    else scheduleFlush();
  }

  function beacon(events: TelemetryEnvelope[]): boolean {
    // text/plain: sendBeacon no puede enviar application/json a otro origen sin una comprobación
    // previa de CORS. El receptor lo lee igualmente como JSON.
    const blob = new Blob([JSON.stringify({ events })], { type: "text/plain;charset=UTF-8" });
    if (options.sendBeacon) return options.sendBeacon(options.endpoint, blob);
    // Sin sendBeacon: fetch con keepalive, que también sobrevive al cierre de la página.
    void options
      .fetch(options.endpoint, { method: "POST", body: blob, keepalive: true, credentials: "omit" })
      .catch(() => discard(events.length, "el envío al cerrar la pestaña falló"));
    return true;
  }

  function flushWithBeacon() {
    clearTimer();
    let pending = queue;
    queue = [];
    if (inFlight && !inFlight.handedOff) {
      inFlight.handedOff = true;
      pending = [...inFlight.events, ...pending];
      inFlight = null;
    }
    for (let start = 0; start < pending.length; start += options.beaconBatchSize) {
      const chunk = pending.slice(start, start + options.beaconBatchSize);
      if (!beacon(chunk)) {
        // El navegador no aceptó el envío (cola de beacons llena): lo que falta vuelve a la cola y
        // saldrá con el siguiente envío si la pestaña sigue viva.
        queue = [...pending.slice(start), ...queue];
        scheduleFlush();
        return;
      }
    }
  }

  return { enqueue, flush, flushWithBeacon, size: () => queue.length };
}
