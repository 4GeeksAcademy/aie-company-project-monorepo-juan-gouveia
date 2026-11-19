"use client";

import { usePathname } from "next/navigation";
import { useReportWebVitals } from "next/web-vitals";
import { useEffect, useRef } from "react";
import { track } from "@/lib/telemetry";
import { captureFrontendError } from "@/lib/telemetry/errors";
import { nextPageView, type LastView } from "@/lib/telemetry/page-views";
import { recordWebVital } from "@/lib/telemetry/performance";
import { currentUserRole } from "@/lib/telemetry/session";

// Piso técnico transversal de la telemetría (plan, sección 13): un solo componente en el layout raíz,
// para todo el backoffice, en lugar de instrumentar cada página.
// - `page_viewed` en cada vista: la carga inicial (`initial`) y cada navegación sin recarga (`client`);
// - `frontend_error_captured` para los errores de JavaScript sin capturar (window.onerror y
//   unhandledrejection); las pantallas de error de Next lo emiten con `error_boundary`;
// - Web Vitals (LCP, CLS e INP) para `page_performance_recorded` (lib/telemetry/performance.ts).
// No dibuja nada.

export default function TelemetryRoot() {
  const pathname = usePathname();
  const previous = useRef<LastView | null>(null);

  useReportWebVitals(recordWebVital);

  useEffect(() => {
    const view = nextPageView(previous.current, pathname, Date.now(), currentUserRole());
    if (!view) return;
    track("page_viewed", view.properties);
    previous.current = view.view;
  }, [pathname]);

  useEffect(() => {
    function onError(event: ErrorEvent) {
      captureFrontendError(event.error ?? event.message, "window_error");
    }
    function onRejection(event: PromiseRejectionEvent) {
      captureFrontendError(event.reason, "unhandled_rejection");
    }
    window.addEventListener("error", onError);
    window.addEventListener("unhandledrejection", onRejection);
    return () => {
      window.removeEventListener("error", onError);
      window.removeEventListener("unhandledrejection", onRejection);
    };
  }, []);

  return null;
}
