import { pageRouteTemplate } from "@/lib/telemetry/routes";

// `page_viewed` (plan, §5.3): qué emitir al mostrarse una vista. La llama TelemetryRoot con cada cambio
// de ruta; es pura para poder probarla sin React.

// Throttle (§10): una segunda vista de la misma ruta en menos de 1 s no cuenta (doble montaje de React
// en desarrollo, recargas dobles).
export const REPEATED_VIEW_MS = 1_000;

export interface LastView {
  route: string;
  at: number;
}

export function nextPageView(
  last: LastView | null,
  pathname: string,
  now: number,
  userRole: string | null
): { properties: Record<string, unknown>; view: LastView } | null {
  const route = pageRouteTemplate(pathname);
  if (last && last.route === route && now - last.at < REPEATED_VIEW_MS) return null;
  return {
    properties: {
      route,
      previous_route: last?.route,
      navigation_type: last ? "client" : "initial",
      // Solo en las vistas protegidas y cuando la sesión ya se validó (el rol no está en el token).
      user_role: userRole ?? undefined,
    },
    view: { route, at: now },
  };
}
