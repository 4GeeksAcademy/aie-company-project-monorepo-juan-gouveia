// Cliente y presentación del reporte técnico de telemetría (lib/telemetry-report.ts): encolar con POST y
// consultar GET /tasks/{task_id} hasta que termina (ticket #DEV-55). `fetch`, la espera y el reloj están
// simulados: no hay red ni esperas reales.
import { ApiError } from "@/lib/api-client";
import {
  ADMIN_ONLY_MESSAGE,
  barPercent,
  datesError,
  formatInstantUtc,
  formatMs,
  formatRate,
  getTelemetryReport,
  levelSegments,
  periodTotals,
  pollDelay,
  POLL_TIMEOUT_MS,
  progressLabel,
  reportBody,
  SLOW_REPORT_MESSAGE,
} from "@/lib/telemetry-report";
import type { TelemetryReport } from "@/types/telemetry-report";

const clearToken = jest.fn();
jest.mock("@/lib/auth/token", () => ({
  getToken: () => "jwt-de-la-sesion",
  clearToken: () => clearToken(),
}));

const fetchMock = jest.fn();

beforeEach(() => {
  fetchMock.mockReset();
  clearToken.mockReset();
  global.fetch = fetchMock as unknown as typeof fetch;
});

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

const REPORT: TelemetryReport = {
  period: { from: "2026-11-13T14:19:36Z", to: "2026-11-20T14:19:36Z" },
  metrics: {
    events_per_day: [{ date: "2026-11-19", total: 41, info: 37, warn: 4, error: 0 }],
    error_rate_by_type: [{ date: "2026-11-19", event_type: "login_failed", level: "warn", count: 1, rate: 0.0244 }],
    api_latency_by_route: [
      { date: "2026-11-19", method: "GET", route: "/api/v1/inventory/orders", samples: 3, avg_ms: 2381.9, max_ms: 3410.3 },
    ],
    auth_failure_rate: [{ date: "2026-11-19", attempts: 2, failed: 1, failure_rate: 0.5 }],
  },
};

// --- Petición ---------------------------------------------------------------------------------------------

describe("reportBody", () => {
  it("sin fechas envía un cuerpo vacío: la API usa los últimos 7 días", () => {
    expect(reportBody({ from: "", to: "" })).toEqual({});
  });

  it("envía el día siguiente a la fecha final, porque en la vista se incluye y en la API no", () => {
    expect(reportBody({ from: "2026-11-14", to: "2026-11-16" })).toEqual({ start_date: "2026-11-14", end_date: "2026-11-17" });
  });

  it("cambia de mes y de año al sumar el día", () => {
    expect(reportBody({ from: "", to: "2026-11-30" })).toEqual({ end_date: "2026-12-01" });
    expect(reportBody({ from: "", to: "2026-12-31" })).toEqual({ end_date: "2027-01-01" });
  });

  it("puede enviar solo una de las dos fechas", () => {
    expect(reportBody({ from: "2026-11-14", to: "" })).toEqual({ start_date: "2026-11-14" });
  });
});

describe("datesError", () => {
  it("acepta fechas vacías, una sola o un rango ordenado (también de un solo día)", () => {
    expect(datesError({ from: "", to: "" })).toBeNull();
    expect(datesError({ from: "2026-11-14", to: "" })).toBeNull();
    expect(datesError({ from: "2026-11-14", to: "2026-11-14" })).toBeNull();
  });

  it("rechaza un inicio posterior al final y un formato que no es AAAA-MM-DD", () => {
    expect(datesError({ from: "2026-11-16", to: "2026-11-14" })).toMatch(/posterior/);
    expect(datesError({ from: "14/11/2026", to: "" })).toMatch(/AAAA-MM-DD/);
  });
});

describe("pollDelay y progressLabel", () => {
  it("consulta cada 1 s los primeros 10 s y después cada 2 s", () => {
    expect([0, 9_999, 10_000, 60_000].map(pollDelay)).toEqual([1_000, 1_000, 2_000, 2_000]);
  });

  it("dice si el reporte se está pidiendo, está en cola o se está calculando", () => {
    expect(progressLabel(null)).toMatch(/Pidiendo/);
    expect(progressLabel("pending")).toMatch(/En cola/);
    expect(progressLabel("started")).toMatch(/Calculando/);
  });
});

describe("getTelemetryReport", () => {
  const TASK_ID = "8c88f901-da18-4fe1-ae9a-61e335c0be19";
  const accepted = () => jsonResponse({ task_id: TASK_ID }, 202);
  const task = (status: string, result: unknown = null) => jsonResponse({ task_id: TASK_ID, status, result });

  // Reloj y espera simulados: cada espera avanza el reloj lo que se pidió, sin esperar de verdad.
  function fakeClock() {
    let time = 0;
    const waits: number[] = [];
    return {
      waits,
      now: () => time,
      wait: async (ms: number) => {
        waits.push(ms);
        time += ms;
      },
    };
  }

  it("encola con POST y el token, y consulta la tarea hasta que termina: pending → started → success", async () => {
    fetchMock
      .mockResolvedValueOnce(accepted())
      .mockResolvedValueOnce(task("pending"))
      .mockResolvedValueOnce(task("started"))
      .mockResolvedValueOnce(task("success", REPORT));
    const clock = fakeClock();
    const progress: string[] = [];

    const report = await getTelemetryReport(
      { from: "2026-11-14", to: "2026-11-16" },
      { onProgress: (p) => progress.push(p), wait: clock.wait, now: clock.now },
    );

    expect(report).toEqual(REPORT);
    expect(progress).toEqual(["pending", "started"]);
    expect(clock.waits).toEqual([1_000, 1_000]);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/telemetry/report");
    expect(init.method).toBe("POST");
    expect(JSON.parse(String(init.body))).toEqual({ start_date: "2026-11-14", end_date: "2026-11-17" });
    expect(new Headers(init.headers).get("Authorization")).toBe("Bearer jwt-de-la-sesion");
    expect(fetchMock.mock.calls.slice(1).map(([u]) => u)).toEqual(Array(3).fill(`/api/tasks/${TASK_ID}`));
  });

  it("si la tarea ya terminó (la misma petición hace menos de 60 s), la primera consulta trae el reporte", async () => {
    fetchMock.mockResolvedValueOnce(accepted()).mockResolvedValueOnce(task("success", REPORT));
    const clock = fakeClock();

    await expect(getTelemetryReport({ from: "", to: "" }, { wait: clock.wait, now: clock.now })).resolves.toEqual(REPORT);
    expect(clock.waits).toEqual([]);
  });

  it("pasados 10 s consulta cada 2 s", async () => {
    fetchMock.mockResolvedValueOnce(accepted());
    for (let i = 0; i < 12; i += 1) fetchMock.mockResolvedValueOnce(task("started"));
    fetchMock.mockResolvedValueOnce(task("success", REPORT));
    const clock = fakeClock();

    await getTelemetryReport({ from: "", to: "" }, { wait: clock.wait, now: clock.now });

    expect(clock.waits.slice(0, 10)).toEqual(Array(10).fill(1_000));
    expect(clock.waits.slice(10)).toEqual([2_000, 2_000]);
  });

  it("una tarea fallida muestra el error de la API", async () => {
    fetchMock
      .mockResolvedValueOnce(accepted())
      .mockResolvedValueOnce(task("failure", { error: "OperationalError: connection refused" }));
    const clock = fakeClock();

    const error = await getTelemetryReport({ from: "", to: "" }, { wait: clock.wait, now: clock.now }).catch((e) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error.code).toBe("report_failed");
    expect(error.message).toMatch(/No se pudo calcular el reporte técnico \(OperationalError: connection refused\)/);
    expect(clearToken).not.toHaveBeenCalled();
  });

  it("a los 3 minutos sin terminar deja de consultar y avisa de que tarda más de lo normal", async () => {
    fetchMock.mockResolvedValueOnce(accepted());
    // Una respuesta nueva en cada consulta: el cuerpo de un Response solo se puede leer una vez.
    fetchMock.mockImplementation(async () => task("pending"));
    const clock = fakeClock();

    const error = await getTelemetryReport({ from: "", to: "" }, { wait: clock.wait, now: clock.now }).catch((e) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error.message).toBe(SLOW_REPORT_MESSAGE);
    expect(clock.now()).toBe(POLL_TIMEOUT_MS);
  });

  it("se cancela al cambiar las fechas o salir de la vista: no hace más consultas", async () => {
    const controller = new AbortController();
    fetchMock.mockResolvedValueOnce(accepted()).mockResolvedValue(task("pending"));
    const wait = async () => {
      controller.abort();
    };

    const error = await getTelemetryReport({ from: "", to: "" }, { signal: controller.signal, wait, now: () => 0 }).catch(
      (e) => e,
    );

    expect(error).toBeInstanceOf(DOMException);
    expect(error.name).toBe("AbortError");
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("un 403 al encolar muestra que el reporte es solo para administradores y no cierra la sesión", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ error: { code: "forbidden", message: "Solo un administrador puede hacer esta operación." } }, 403),
    );

    await expect(getTelemetryReport({ from: "", to: "" })).rejects.toMatchObject({
      message: ADMIN_ONLY_MESSAGE,
      status: 403,
    });
    expect(clearToken).not.toHaveBeenCalled();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("los errores al encolar llegan con el mensaje de la API (por ejemplo, un período demasiado largo)", async () => {
    const message = "El período no puede pasar de 90 días.";
    fetchMock.mockResolvedValue(jsonResponse({ error: { code: "period_too_long", message } }, 422));

    const error = await getTelemetryReport({ from: "2026-01-01", to: "2026-11-01" }).catch((e) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error.message).toBe(message);
  });

  it("la cola no disponible (503) llega con el mensaje de la API", async () => {
    const message = "La cola de tareas no está disponible en este momento. Vuelve a intentarlo.";
    fetchMock.mockResolvedValue(jsonResponse({ error: { code: "task_queue_unavailable", message } }, 503));

    await expect(getTelemetryReport({ from: "", to: "" })).rejects.toMatchObject({ message });
  });
});

// --- Presentación -----------------------------------------------------------------------------------------

describe("formato", () => {
  it("muestra los límites del período en UTC", () => {
    expect(formatInstantUtc("2026-11-13T14:19:36Z")).toBe("2026-11-13 14:19 UTC");
    expect(formatInstantUtc("no-es-fecha")).toBe("no-es-fecha");
  });

  it("muestra las tasas como porcentaje con un decimal", () => {
    expect(formatRate(0.3333)).toBe("33.3%");
    expect(formatRate(1)).toBe("100.0%");
    expect(formatRate(0)).toBe("0.0%");
  });

  it("muestra los milisegundos con un decimal y separador de miles", () => {
    expect(formatMs(2381.9)).toBe("2,381.9 ms");
    expect(formatMs(30)).toBe("30.0 ms");
  });
});

describe("barras", () => {
  it("barPercent es proporcional al máximo y nunca pasa de 100 ni baja de 0", () => {
    expect(barPercent(50, 200)).toBe(25);
    expect(barPercent(300, 200)).toBe(100);
    expect(barPercent(5, 0)).toBe(0);
    expect(barPercent(-1, 10)).toBe(0);
  });

  it("levelSegments reparte la barra del día por nivel y omite los niveles en 0", () => {
    const day = { date: "2026-11-19", total: 40, info: 30, warn: 10, error: 0 };

    expect(levelSegments(day, 80)).toEqual([
      { level: "info", percent: 37.5 },
      { level: "warn", percent: 12.5 },
    ]);
  });

  it("periodTotals suma los días por nivel", () => {
    const days = [
      { date: "2026-11-18", total: 0, info: 0, warn: 0, error: 0 },
      { date: "2026-11-19", total: 41, info: 37, warn: 4, error: 0 },
      { date: "2026-11-20", total: 3, info: 1, warn: 1, error: 1 },
    ];

    expect(periodTotals(days)).toEqual({ total: 44, info: 38, warn: 5, error: 1 });
  });
});
