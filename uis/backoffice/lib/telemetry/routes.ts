// Plantillas de ruta para las propiedades `route` de la telemetría (plan, §7.1, regla 5): nunca la URL
// real, sin ids ni query string.

// Nombre del parámetro según el recurso que lo precede, como en los routers de la API.
const PARAM_BY_RESOURCE: Record<string, string> = {
  products: "{ingredient_id}",
  suppliers: "{supplier_id}",
  incidents: "{incident_id}",
  users: "{user_id}",
  profiles: "{user_id}",
  tasks: "{task_id}",
};

// Recursos que la API publica en la raíz, no bajo /api/v1.
const API_ROOT_RESOURCES = new Set(["telemetry", "reporting", "tasks"]);

const ID_SEGMENT = /^(\d+|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$/i;

// Ruta del intermediario (/inventory/products/12?x=1) → ruta de la API como plantilla
// (/api/v1/inventory/products/{ingredient_id}). Los eventos que nacen de una llamada a la API usan la
// ruta de la API, la misma que registra su línea de log.
export function apiRouteTemplate(path: string): string {
  const segments = path.split(/[?#]/)[0].split("/").filter(Boolean);
  const templated = segments.map((segment, index) =>
    ID_SEGMENT.test(segment) ? (PARAM_BY_RESOURCE[segments[index - 1]] ?? "{id}") : segment
  );
  // La API sirve /telemetry, /reporting y /tasks fuera de /api/v1 (llegan por sus propias rutas del intermediario).
  const prefix = API_ROOT_RESOURCES.has(segments[0]) ? "" : "/api/v1";
  return `${prefix}/${templated.join("/")}`;
}

// Rutas dinámicas del backoffice (app/): el segmento variable se sustituye por el nombre de su carpeta.
const DYNAMIC_PAGES: ReadonlyArray<[RegExp, string]> = [[/^\/talento\/candidates\/[^/]+/, "/talento/candidates/[id]"]];

// Ruta de una vista del backoffice como plantilla: sin query string, sin barra final y con los ids
// sustituidos (/talento/candidates/abc → /talento/candidates/[id]). Los ids de candidatos vienen de
// una API externa y pueden identificar a una persona: nunca salen en un evento.
export function pageRouteTemplate(pathname: string): string {
  const path = pathname.split(/[?#]/)[0].replace(/\/+$/, "") || "/";
  for (const [pattern, template] of DYNAMIC_PAGES) {
    if (pattern.test(path)) return path.replace(pattern, template);
  }
  return path;
}
