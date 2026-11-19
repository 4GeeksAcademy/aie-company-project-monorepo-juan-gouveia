import { track } from "@/lib/telemetry";
import { onBeforeHide } from "@/lib/telemetry/lifecycle";
import { pageRouteTemplate } from "@/lib/telemetry/routes";

// `page_performance_recorded` (plan, §5.4, y actividad adicional de Web Vitals): LCP, CLS e INP de la
// vista con la que se cargó el backoffice, medidos en los dispositivos y redes reales de los locales.
//
// Next entrega cada métrica por separado con useReportWebVitals (components/telemetry/TelemetryRoot)
// y solo de la carga inicial: las navegaciones sin recarga no tienen Web Vitals propias. Aquí se
// juntan y se emiten en un único evento (§10: uno por vista) cuando la pestaña se oculta o se
// cierra, que es cuando CLS e INP son definitivas, justo antes del envío con sendBeacon. FCP y TTFB
// no se envían: no están en el allowlist del evento.

type VitalName = "LCP" | "CLS" | "INP";

const ALLOWED: Record<VitalName, "lcp_ms" | "cls" | "inp_ms"> = { LCP: "lcp_ms", CLS: "cls", INP: "inp_ms" };
const CONNECTIONS = new Set(["slow-2g", "2g", "3g", "4g"]);

let route: string | null = null;
let metrics: Partial<Record<"lcp_ms" | "cls" | "inp_ms", number>> = {};
let emitted = false;

export function deviceClass(width: number): "mobile" | "tablet" | "desktop" {
  if (width < 768) return "mobile";
  if (width < 1024) return "tablet";
  return "desktop";
}

function effectiveConnection(): string | undefined {
  const type = (navigator as Navigator & { connection?: { effectiveType?: string } }).connection?.effectiveType;
  return type && CONNECTIONS.has(type) ? type : undefined;
}

// La recibe TelemetryRoot desde useReportWebVitals.
export function recordWebVital(metric: { name: string; value: number }): void {
  const key = ALLOWED[metric.name as VitalName];
  if (!key || emitted) return;
  // Las métricas son de la página que se cargó: su ruta es la de ese momento.
  route ??= pageRouteTemplate(window.location.pathname);
  metrics[key] = key === "cls" ? Math.round(metric.value * 10_000) / 10_000 : Math.round(metric.value);
}

export function emitPagePerformance(): void {
  if (emitted || route === null || Object.keys(metrics).length === 0) return;
  emitted = true;
  track("page_performance_recorded", {
    route,
    ...metrics,
    device_class: deviceClass(window.innerWidth),
    effective_connection: effectiveConnection(),
  });
}

// Solo para las pruebas.
export function resetPagePerformance(): void {
  route = null;
  metrics = {};
  emitted = false;
}

if (typeof window !== "undefined") onBeforeHide(emitPagePerformance);
