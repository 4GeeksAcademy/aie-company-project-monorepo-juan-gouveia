// Cliente y presentación del reporte técnico de telemetría (lib/telemetry-report.ts). `fetch` está
// simulado: no hay red.
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
  reportQuery,
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

describe("reportQuery", () => {
  it("sin fechas no envía parámetros: la API usa los últimos 7 días", () => {
    expect(reportQuery({ from: "", to: "" })).toBe("");
  });

  it("envía el día siguiente a la fecha final, porque en la vista se incluye y en la API no", () => {
    expect(reportQuery({ from: "2026-11-14", to: "2026-11-16" })).toBe("?start_date=2026-11-14&end_date=2026-11-17");
  });

  it("cambia de mes y de año al sumar el día", () => {
    expect(reportQuery({ from: "", to: "2026-11-30" })).toBe("?end_date=2026-12-01");
    expect(reportQuery({ from: "", to: "2026-12-31" })).toBe("?end_date=2027-01-01");
  });

  it("puede enviar solo una de las dos fechas", () => {
    expect(reportQuery({ from: "2026-11-14", to: "" })).toBe("?start_date=2026-11-14");
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

describe("getTelemetryReport", () => {
  it("pide el reporte al intermediario con el token y devuelve el JSON", async () => {
    fetchMock.mockResolvedValue(jsonResponse(REPORT));

    await expect(getTelemetryReport({ from: "2026-11-14", to: "2026-11-16" })).resolves.toEqual(REPORT);

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/telemetry/report?start_date=2026-11-14&end_date=2026-11-17");
    expect(new Headers(init.headers).get("Authorization")).toBe("Bearer jwt-de-la-sesion");
  });

  it("un 403 muestra que el reporte es solo para administradores y no cierra la sesión", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ error: { code: "forbidden", message: "Solo un administrador puede hacer esta operación." } }, 403),
    );

    await expect(getTelemetryReport({ from: "", to: "" })).rejects.toMatchObject({
      message: ADMIN_ONLY_MESSAGE,
      status: 403,
    });
    expect(clearToken).not.toHaveBeenCalled();
  });

  it("los demás errores llegan con el mensaje de la API (por ejemplo, un período demasiado largo)", async () => {
    const message = "El período no puede pasar de 90 días.";
    fetchMock.mockResolvedValue(jsonResponse({ error: { code: "period_too_long", message } }, 422));

    const error = await getTelemetryReport({ from: "2026-01-01", to: "2026-11-01" }).catch((e) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error.message).toBe(message);
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
