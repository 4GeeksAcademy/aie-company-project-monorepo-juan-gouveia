// Cliente y presentación del Reporte Semanal de Costo y Merma por Local (lib/weekly-report.ts). `fetch`
// está simulado: no hay red.
import { ApiError } from "@/lib/api-client";
import {
  barPercent,
  currentWeekStart,
  formatKpi,
  formatMoney,
  formatRatio,
  formatWeekPeriod,
  freshnessOf,
  getLatestPipelineRun,
  getWeeklyReport,
  isCurrentWeek,
  isSilentWeek,
  KPIS,
  rankBy,
  READERS_ONLY_MESSAGE,
  shiftWeek,
  summarizeByCountry,
} from "@/lib/weekly-report";
import type { LocationWeekPerformance, PipelineRun, WeeklyLocationPerformance } from "@/types/weekly-report";

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

function location(overrides: Partial<LocationWeekPerformance>): LocationWeekPerformance {
  return {
    location_id: "medellin_centro",
    location_name: "Medellín Centro",
    country: "CO",
    total_purchase_cost: 0,
    total_waste_cost: 0,
    waste_ratio: 0,
    stockout_events_count: 0,
    price_alert_events_count: 0,
    currency: "COP",
    ...overrides,
  };
}

// La semana del 23 de noviembre de 2026 de la verificación real (entorno development).
const REPORT: WeeklyLocationPerformance = {
  week_start: "2026-11-23",
  locations: [
    location({ total_purchase_cost: 850, total_waste_cost: 106.25, waste_ratio: 0.125, stockout_events_count: 1, price_alert_events_count: 1 }),
    location({ location_id: "bogota_chapinero", location_name: "Bogotá Chapinero", total_purchase_cost: 300, stockout_events_count: 1 }),
    location({ location_id: "cali_granada", location_name: "Cali Granada" }),
    location({
      location_id: "miami_doral", location_name: "Miami Doral", country: "US", currency: "USD",
      total_purchase_cost: 100, total_waste_cost: 20, waste_ratio: 0.2,
    }),
    location({
      location_id: "orlando_international", location_name: "Orlando International Drive", country: "US", currency: "USD",
      stockout_events_count: 1,
    }),
  ],
};

function run(overrides: Partial<PipelineRun>): PipelineRun {
  return {
    id: "479b73c0-e45d-45b0-a6cc-3fb895451395",
    pipeline: "weekly_location_performance",
    trigger: "scheduled",
    status: "completed",
    week_from: "2026-10-26",
    week_to: "2026-11-16",
    created_at: "2026-11-23T11:00:00Z",
    started_at: "2026-11-23T11:00:01Z",
    finished_at: "2026-11-23T11:00:03Z",
    events_read: 15,
    events_rejected: 1,
    events_discarded: 0,
    waste_events_without_cost: 0,
    issues: {},
    rows_written: 56,
    failed_task: null,
    error_message: null,
    ...overrides,
  };
}

// --- Peticiones -------------------------------------------------------------------------------------------

describe("getWeeklyReport", () => {
  it("pide la semana al intermediario con el token", async () => {
    fetchMock.mockResolvedValue(jsonResponse(REPORT));

    await expect(getWeeklyReport("2026-11-23")).resolves.toEqual({ status: "computed", report: REPORT });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/reporting/weekly-location-performance?week_start=2026-11-23");
    expect(new Headers(init.headers).get("Authorization")).toBe("Bearer jwt-de-la-sesion");
  });

  it("sin semana pide la última calculada", async () => {
    fetchMock.mockResolvedValue(jsonResponse(REPORT));

    await getWeeklyReport(null);

    expect(fetchMock.mock.calls[0][0]).toBe("/api/reporting/weekly-location-performance");
  });

  it("una semana sin calcular no es un error: la vista lo dice", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ error: { code: "week_not_computed", message: "La semana 2026-09-07 no está calculada." } }, 404),
    );

    await expect(getWeeklyReport("2026-09-07")).resolves.toEqual({ status: "not_computed", weekStart: "2026-09-07" });
  });

  it("un 403 dice que el reporte es para administradores y gerentes, y no cierra la sesión", async () => {
    fetchMock.mockResolvedValue(jsonResponse({ error: { code: "forbidden", message: "No tienes permiso." } }, 403));

    await expect(getWeeklyReport(null)).rejects.toMatchObject({ message: READERS_ONLY_MESSAGE, status: 403 });
    expect(clearToken).not.toHaveBeenCalled();
  });

  it("los demás errores llegan con el mensaje de la API", async () => {
    const message = "No se pudo consultar el reporte de negocio. Vuelve a intentarlo.";
    fetchMock.mockResolvedValue(jsonResponse({ error: { code: "reporting_unavailable", message } }, 503));

    const error = await getWeeklyReport(null).catch((e) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(503);
  });
});

describe("getLatestPipelineRun", () => {
  it("devuelve la última corrida, o null si el pipeline nunca corrió", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(run({})));
    await expect(getLatestPipelineRun()).resolves.toMatchObject({ status: "completed" });
    expect(fetchMock.mock.calls[0][0]).toBe("/api/reporting/pipeline-runs/latest");

    fetchMock.mockResolvedValueOnce(
      jsonResponse({ error: { code: "no_pipeline_runs", message: "El pipeline todavía no ha corrido." } }, 404),
    );
    await expect(getLatestPipelineRun()).resolves.toBeNull();
  });
});

// --- KPIs y formato ---------------------------------------------------------------------------------------

describe("KPIS", () => {
  it("usa los cinco nombres del briefing, en su orden", () => {
    expect(KPIS.map((kpi) => kpi.label)).toEqual([
      "Costo de compra por local",
      "Costo de merma por local",
      "Ratio de merma",
      "Frecuencia de quiebre de stock",
      "Frecuencia de alertas de precio",
    ]);
    expect(KPIS.map((kpi) => kpi.key)).toEqual([
      "total_purchase_cost",
      "total_waste_cost",
      "waste_ratio",
      "stockout_events_count",
      "price_alert_events_count",
    ]);
  });
});

// Intl separa la moneda del número con un espacio duro; se normaliza para comparar.
const plain = (text: string) => text.replace(/ /g, " ");

describe("formato", () => {
  it("muestra cada importe en la moneda de su local, en formato colombiano", () => {
    expect(plain(formatMoney(1530000, "COP"))).toBe("$ 1.530.000");
    expect(plain(formatMoney(106.25, "COP"))).toBe("$ 106,25");
    expect(plain(formatMoney(100, "USD"))).toBe("US$ 100,00");
  });

  it("muestra el ratio como porcentaje, también por encima del 100 %", () => {
    expect(formatRatio(0.125)).toBe("12,5 %");
    expect(formatRatio(0)).toBe("0 %");
    expect(formatRatio(3)).toBe("300 %");
  });

  it("da formato a cada KPI según su tipo", () => {
    expect(formatKpi("count", 2, "COP")).toBe("2");
    expect(formatKpi("ratio", 0.2, "USD")).toBe("20 %");
    expect(plain(formatKpi("money", 20, "USD"))).toBe("US$ 20,00");
  });
});

// --- Semanas ----------------------------------------------------------------------------------------------

describe("semanas", () => {
  it("describe el período en palabras, también entre meses y años", () => {
    expect(formatWeekPeriod("2026-11-16")).toBe("Semana del lunes 16 al domingo 22 de noviembre de 2026");
    expect(formatWeekPeriod("2026-11-30")).toBe("Semana del lunes 30 de noviembre al domingo 6 de diciembre de 2026");
    expect(formatWeekPeriod("2026-12-28")).toBe("Semana del lunes 28 de diciembre de 2026 al domingo 3 de enero de 2027");
  });

  it("se mueve de lunes en lunes", () => {
    expect(shiftWeek("2026-11-16", -1)).toBe("2026-11-09");
    expect(shiftWeek("2026-11-30", 1)).toBe("2026-12-07");
  });

  it("la semana en curso empieza el lunes UTC, aunque hoy sea domingo", () => {
    expect(currentWeekStart(new Date("2026-11-23T00:00:00Z"))).toBe("2026-11-23");
    expect(currentWeekStart(new Date("2026-11-29T23:59:59Z"))).toBe("2026-11-23");
    expect(isCurrentWeek("2026-11-23", new Date("2026-11-25T12:00:00Z"))).toBe(true);
    expect(isCurrentWeek("2026-11-16", new Date("2026-11-25T12:00:00Z"))).toBe(false);
  });
});

// --- Datos de la vista ------------------------------------------------------------------------------------

describe("summarizeByCountry", () => {
  it("consolida cada país en su moneda, sin sumar pesos con dólares", () => {
    const [colombia, unitedStates] = summarizeByCountry(REPORT);

    expect(colombia).toMatchObject({
      country: "CO",
      currency: "COP",
      locations: 3,
      total_purchase_cost: 1150,
      total_waste_cost: 106.25,
      stockout_events_count: 2,
      price_alert_events_count: 1,
    });
    // Merma del país sobre sus compras: 106,25 / 1150, no la media de los ratios de sus locales.
    expect(colombia.waste_ratio).toBe(0.0924);
    expect(unitedStates).toMatchObject({ country: "US", currency: "USD", total_purchase_cost: 100, waste_ratio: 0.2 });
  });
});

describe("rankBy y barPercent", () => {
  it("ordena los locales de mayor a menor y, a igual valor, por nombre", () => {
    const colombia = REPORT.locations.filter((row) => row.country === "CO");

    expect(rankBy(colombia, "total_purchase_cost").map((row) => row.location_id)).toEqual([
      "medellin_centro",
      "bogota_chapinero",
      "cali_granada",
    ]);
    expect(rankBy(colombia, "stockout_events_count").map((row) => row.location_id)).toEqual([
      "bogota_chapinero",
      "medellin_centro",
      "cali_granada",
    ]);
  });

  it("mide cada barra respecto al mayor valor de su grupo", () => {
    expect(barPercent(300, 850)).toBeCloseTo(35.29, 2);
    expect(barPercent(0, 850)).toBe(0);
    expect(barPercent(5, 0)).toBe(0);
  });
});

describe("isSilentWeek", () => {
  it("avisa solo si ningún local tuvo actividad", () => {
    expect(isSilentWeek(REPORT)).toBe(false);
    expect(isSilentWeek({ week_start: "2026-11-02", locations: [location({}), location({ location_id: "miami_doral" })] })).toBe(
      true,
    );
  });
});

describe("freshnessOf", () => {
  const monday = new Date("2026-11-23T15:00:00Z");

  it("dice cuándo se actualizaron los datos", () => {
    expect(freshnessOf(run({}), monday)).toEqual({ status: "fresh", at: "2026-11-23T11:00:03Z" });
  });

  it("avisa si la última corrida correcta tiene más de 8 días", () => {
    const old = run({ finished_at: "2026-11-09T11:00:03Z" });
    expect(freshnessOf(old, monday)).toEqual({ status: "stale", at: "2026-11-09T11:00:03Z" });
  });

  it("distingue una actualización fallida, una en curso, un pipeline que nunca corrió y un estado desconocido", () => {
    expect(freshnessOf(run({ status: "failed" }), monday).status).toBe("failed");
    expect(freshnessOf(run({ status: "running", finished_at: null }), monday).status).toBe("updating");
    expect(freshnessOf(null, monday)).toEqual({ status: "never" });
    expect(freshnessOf(undefined, monday)).toEqual({ status: "unknown" });
  });
});
