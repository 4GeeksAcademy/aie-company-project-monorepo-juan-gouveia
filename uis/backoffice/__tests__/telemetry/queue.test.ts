// Cola local y envío por lotes de la telemetría (lib/telemetry/queue.ts): lote de 20 o cada 10 s,
// reintentos con espera exponencial, cola máxima y envío con sendBeacon al ocultar la pestaña.
// fetch y sendBeacon están simulados, y los temporizadores son falsos: no hay red ni esperas reales.
import type { TelemetryEnvelope } from "@/lib/telemetry/envelope";
import { createTelemetryQueue, type TelemetryQueueOptions } from "@/lib/telemetry/queue";

const ENDPOINT = "http://localhost:8000/telemetry/events";

const fetchMock = jest.fn();
const sendBeacon = jest.fn();
const onDiscard = jest.fn();

function event(n: number): TelemetryEnvelope {
  return {
    eventId: `00000000-0000-4000-8000-${String(n).padStart(12, "0")}`,
    timestamp: "2026-11-19T10:15:30.123Z",
    sessionId: null,
    userId: null,
    event_type: "page_viewed",
    schemaVersion: "1.0.0",
    requestId: null,
    properties: { route: "/login", navigation_type: "initial" },
    source: "browser",
    environment: "development",
  };
}

function queue(overrides: Partial<TelemetryQueueOptions> = {}) {
  return createTelemetryQueue({
    endpoint: ENDPOINT,
    batchSize: 20,
    flushIntervalMs: 10_000,
    retryDelaysMs: [1_000, 2_000, 4_000],
    maxQueueSize: 500,
    beaconBatchSize: 20,
    fetch: fetchMock as unknown as typeof fetch,
    sendBeacon,
    onDiscard,
    ...overrides,
  });
}

function sentBatches(): string[][] {
  return fetchMock.mock.calls.map(([, init]) => JSON.parse((init as RequestInit).body as string).events.map((e: TelemetryEnvelope) => e.eventId));
}

function ok(status = 200) {
  return Promise.resolve(new Response(JSON.stringify({ received: 1 }), { status }));
}

beforeEach(() => {
  jest.useFakeTimers();
  fetchMock.mockReset().mockImplementation(() => ok());
  sendBeacon.mockReset().mockReturnValue(true);
  onDiscard.mockReset();
});

afterEach(() => {
  jest.useRealTimers();
});

describe("lote", () => {
  it("no envía nada mientras hay menos de 20 eventos y no pasan 10 s", async () => {
    const q = queue();
    for (let n = 0; n < 19; n++) q.enqueue(event(n));

    await jest.advanceTimersByTimeAsync(9_999);

    expect(fetchMock).not.toHaveBeenCalled();
    expect(q.size()).toBe(19);
  });

  it("envía el lote al llegar a 20 eventos, en una sola petición", async () => {
    const q = queue();
    for (let n = 0; n < 20; n++) q.enqueue(event(n));
    await jest.advanceTimersByTimeAsync(0);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(sentBatches()[0]).toHaveLength(20);
    expect(q.size()).toBe(0);
  });

  it("envía lo pendiente a los 10 s aunque no haya 20 eventos", async () => {
    const q = queue();
    q.enqueue(event(1));
    q.enqueue(event(2));

    await jest.advanceTimersByTimeAsync(10_000);

    expect(sentBatches()).toEqual([[event(1).eventId, event(2).eventId]]);
  });

  it("envía {events: [...]} en JSON con POST a la URL configurada, sin credenciales", async () => {
    const q = queue();
    q.enqueue(event(1));
    await jest.advanceTimersByTimeAsync(10_000);

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe(ENDPOINT);
    expect(init.method).toBe("POST");
    expect(new Headers(init.headers).get("Content-Type")).toBe("application/json");
    expect(init.credentials).toBe("omit");
    expect(JSON.parse(init.body as string)).toEqual({ events: [event(1)] });
  });

  it("los eventos que llegan durante un envío salen en el lote siguiente", async () => {
    let resolveFirst: (response: Response) => void = () => {};
    fetchMock.mockImplementationOnce(() => new Promise<Response>((resolve) => (resolveFirst = resolve)));
    const q = queue();
    for (let n = 0; n < 20; n++) q.enqueue(event(n));
    q.enqueue(event(100));

    resolveFirst(new Response("{}", { status: 200 }));
    await jest.advanceTimersByTimeAsync(10_000);

    expect(sentBatches()).toHaveLength(2);
    expect(sentBatches()[1]).toEqual([event(100).eventId]);
  });
});

describe("reintentos", () => {
  it("reintenta 3 veces con esperas de 1, 2 y 4 s y después descarta el lote", async () => {
    fetchMock.mockImplementation(() => Promise.reject(new TypeError("Failed to fetch")));
    const q = queue();
    q.enqueue(event(1));

    await jest.advanceTimersByTimeAsync(10_000);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    await jest.advanceTimersByTimeAsync(1_000);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    await jest.advanceTimersByTimeAsync(2_000);
    expect(fetchMock).toHaveBeenCalledTimes(3);
    await jest.advanceTimersByTimeAsync(4_000);
    expect(fetchMock).toHaveBeenCalledTimes(4);
    await jest.advanceTimersByTimeAsync(60_000);

    expect(fetchMock).toHaveBeenCalledTimes(4);
    expect(onDiscard).toHaveBeenCalledWith(1, expect.stringContaining("3 reintentos"));
  });

  it("los reintentos conservan el eventId", async () => {
    fetchMock.mockImplementationOnce(() => ok(503));
    const q = queue();
    q.enqueue(event(7));

    await jest.advanceTimersByTimeAsync(11_000);

    expect(sentBatches()).toEqual([[event(7).eventId], [event(7).eventId]]);
    expect(onDiscard).not.toHaveBeenCalled();
  });

  it("no reintenta un lote que el receptor rechaza por su formato (4xx)", async () => {
    fetchMock.mockImplementation(() => ok(422));
    const q = queue();
    q.enqueue(event(1));

    await jest.advanceTimersByTimeAsync(30_000);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(onDiscard).toHaveBeenCalledWith(1, expect.stringContaining("422"));
  });

  it.each([429, 408, 500])("reintenta un %i", async (status) => {
    fetchMock.mockImplementationOnce(() => ok(status));
    const q = queue();
    q.enqueue(event(1));

    await jest.advanceTimersByTimeAsync(11_000);

    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});

describe("cola máxima", () => {
  it("descarta los eventos más antiguos al superar el máximo", async () => {
    let release: (response: Response) => void = () => {};
    fetchMock.mockImplementation(() => new Promise<Response>((resolve) => (release = resolve)));
    const q = queue({ batchSize: 2, maxQueueSize: 3 });
    // Los dos primeros salen y se quedan esperando la respuesta; los demás se acumulan.
    for (let n = 0; n < 6; n++) q.enqueue(event(n));

    expect(q.size()).toBe(3);
    expect(onDiscard).toHaveBeenCalledWith(1, expect.stringContaining("tamaño máximo"));
    release(new Response("{}"));
  });
});

describe("sendBeacon al ocultar la pestaña", () => {
  it("envía lo pendiente como text/plain y vacía la cola", async () => {
    const q = queue();
    q.enqueue(event(1));
    q.enqueue(event(2));

    q.flushWithBeacon();

    expect(sendBeacon).toHaveBeenCalledTimes(1);
    const [url, blob] = sendBeacon.mock.calls[0] as [string, Blob];
    expect(url).toBe(ENDPOINT);
    expect(blob.type).toBe("text/plain;charset=utf-8");
    expect(JSON.parse(await blob.text())).toEqual({ events: [event(1), event(2)] });
    expect(q.size()).toBe(0);
    await jest.advanceTimersByTimeAsync(10_000);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("divide lo pendiente en lotes de 20", () => {
    const q = queue({ batchSize: 100 });
    for (let n = 0; n < 45; n++) q.enqueue(event(n));

    q.flushWithBeacon();

    expect(sendBeacon.mock.calls.map(([, blob]) => (blob as Blob).size > 0)).toEqual([true, true, true]);
  });

  it("incluye el lote que esperaba un reintento y deja de reintentarlo", async () => {
    fetchMock.mockImplementationOnce(() => ok(503));
    const q = queue();
    q.enqueue(event(1));
    await jest.advanceTimersByTimeAsync(10_000);

    q.enqueue(event(2));
    q.flushWithBeacon();
    await jest.advanceTimersByTimeAsync(30_000);

    const [, blob] = sendBeacon.mock.calls[0] as [string, Blob];
    expect(JSON.parse(await blob.text()).events.map((e: TelemetryEnvelope) => e.eventId)).toEqual([event(1).eventId, event(2).eventId]);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("si el navegador no acepta el beacon, los eventos vuelven a la cola", () => {
    sendBeacon.mockReturnValue(false);
    const q = queue();
    q.enqueue(event(1));

    q.flushWithBeacon();

    expect(q.size()).toBe(1);
  });

  it("sin sendBeacon usa fetch con keepalive", () => {
    const q = queue({ sendBeacon: undefined });
    q.enqueue(event(1));

    q.flushWithBeacon();

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(init.keepalive).toBe(true);
  });
});
