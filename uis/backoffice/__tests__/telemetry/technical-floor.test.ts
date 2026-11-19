/**
 * @jest-environment jsdom
 */
// Piso técnico transversal: vistas (`page_viewed`), errores de JavaScript (`frontend_error_captured`)
// y Web Vitals (`page_performance_recorded`). track() está simulado.
import { captureFrontendError, fingerprint, resetErrorThrottle, sanitizeMessage } from "@/lib/telemetry/errors";
import { handleHide } from "@/lib/telemetry/lifecycle";
import { nextPageView } from "@/lib/telemetry/page-views";
import { deviceClass, emitPagePerformance, recordWebVital, resetPagePerformance } from "@/lib/telemetry/performance";
import { pageRouteTemplate } from "@/lib/telemetry/routes";

const track = jest.fn();
jest.mock("@/lib/telemetry", () => ({ track: (...args: unknown[]) => track(...args) }));

beforeEach(() => {
  track.mockReset();
  resetErrorThrottle();
  resetPagePerformance();
  window.history.replaceState(null, "", "/inventario/ordenes");
});

describe("page_viewed", () => {
  it("la primera vista es initial y las siguientes client, con la ruta anterior", () => {
    const first = nextPageView(null, "/inventario/ingredientes", 0, null);
    expect(first?.properties).toEqual({ route: "/inventario/ingredientes", previous_route: undefined, navigation_type: "initial", user_role: undefined });

    const second = nextPageView(first!.view, "/inventario/ordenes", 5_000, "manager");
    expect(second?.properties).toEqual({ route: "/inventario/ordenes", previous_route: "/inventario/ingredientes", navigation_type: "client", user_role: "manager" });
  });

  it("ignora una segunda vista de la misma ruta en menos de 1 s", () => {
    const first = nextPageView(null, "/proveedores", 0, null)!;
    expect(nextPageView(first.view, "/proveedores", 500, null)).toBeNull();
    expect(nextPageView(first.view, "/proveedores", 1_500, null)).not.toBeNull();
  });

  it.each([
    ["/talento/candidates/9f1c-abc", "/talento/candidates/[id]"],
    ["/inventario/ordenes/", "/inventario/ordenes"],
    ["/", "/"],
  ])("usa la plantilla de la ruta, sin ids (%s)", (pathname, route) => {
    expect(pageRouteTemplate(pathname)).toBe(route);
  });
});

describe("frontend_error_captured", () => {
  it("sanea el mensaje: emails, UUID y números de 4 o más cifras, y máximo 200 caracteres", () => {
    expect(sanitizeMessage("Fallo de ana@brasaland.com en el pedido 13319 (d445afb4-d2f2-4caa-bbf5-9e0023fcfbb2) x 12")).toBe(
      "Fallo de [redacted] en el pedido [redacted] ([redacted]) x 12"
    );
    expect(sanitizeMessage("x".repeat(500))).toHaveLength(200);
  });

  it("la huella tiene 16 caracteres hexadecimales y es estable", () => {
    expect(fingerprint("TypeError|at render (page.js)")).toMatch(/^[0-9a-f]{16}$/);
    expect(fingerprint("a")).toBe(fingerprint("a"));
    expect(fingerprint("a")).not.toBe(fingerprint("b"));
  });

  it("emite el error con su ruta, su tipo, el mensaje saneado y el origen", () => {
    captureFrontendError(new TypeError("Cannot read properties of undefined (reading 'status')"), "error_boundary", 0);

    expect(track).toHaveBeenCalledWith("frontend_error_captured", {
      route: "/inventario/ordenes",
      error_name: "TypeError",
      message_sanitized: "Cannot read properties of undefined (reading 'status')",
      error_fingerprint: expect.stringMatching(/^[0-9a-f]{16}$/),
      source: "error_boundary",
    });
  });

  it("el mismo error no se repite antes de 60 s", () => {
    const error = new Error("fallo en bucle");
    captureFrontendError(error, "window_error", 0);
    captureFrontendError(error, "window_error", 30_000);
    captureFrontendError(error, "window_error", 61_000);

    expect(track).toHaveBeenCalledTimes(2);
  });

  it("los errores lanzados en el mismo punto comparten huella: no se repiten", () => {
    for (let n = 0; n < 5; n++) captureFrontendError(new Error(`fallo ${n}`), "window_error", n);

    expect(track).toHaveBeenCalledTimes(1);
  });

  it("como máximo 20 errores por página", () => {
    // Sin pila, la huella sale del mensaje: 30 errores distintos.
    for (let n = 0; n < 30; n++) captureFrontendError(`fallo ${String.fromCharCode(97 + n)}`, "unhandled_rejection", n);

    expect(track).toHaveBeenCalledTimes(20);
  });

  it("acepta valores que no son Error", () => {
    captureFrontendError("texto lanzado", "unhandled_rejection", 0);
    captureFrontendError({ raro: true }, "unhandled_rejection", 0);

    expect(track.mock.calls.map(([, props]) => props.error_name)).toEqual(["Error", "NonError"]);
  });
});

describe("page_performance_recorded", () => {
  it("junta LCP, CLS e INP en un solo evento con la clase de dispositivo", () => {
    window.innerWidth = 900;
    recordWebVital({ name: "LCP", value: 820.4 });
    recordWebVital({ name: "CLS", value: 0.01234 });
    recordWebVital({ name: "INP", value: 40.2 });
    recordWebVital({ name: "FCP", value: 300 });
    recordWebVital({ name: "TTFB", value: 80 });

    emitPagePerformance();

    expect(track).toHaveBeenCalledTimes(1);
    expect(track).toHaveBeenCalledWith("page_performance_recorded", {
      route: "/inventario/ordenes",
      lcp_ms: 820,
      cls: 0.0123,
      inp_ms: 40,
      device_class: "tablet",
      effective_connection: undefined,
    });
  });

  it("se emite al ocultar la pestaña, una sola vez", () => {
    recordWebVital({ name: "LCP", value: 500 });

    handleHide();
    handleHide();

    expect(track).toHaveBeenCalledTimes(1);
  });

  it("sin métricas no emite nada", () => {
    emitPagePerformance();
    expect(track).not.toHaveBeenCalled();
  });

  it.each([
    [375, "mobile"],
    [768, "tablet"],
    [1024, "desktop"],
  ])("%i px es %s", (width, expected) => {
    expect(deviceClass(width)).toBe(expected);
  });
});
