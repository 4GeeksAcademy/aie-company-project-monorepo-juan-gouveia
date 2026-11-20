// Reenvío del intermediario (Backend for Frontend) a la API de Brasaland. Solo reenvía la petición:
// no aplica reglas de negocio ni decide permisos (propuesta 5.2). Así la URL de la API es una variable
// de servidor y el navegador no necesita CORS. El token JWT lo envía el navegador en Authorization
// (ticket AUTH-02) y se reenvía tal cual; la API es quien lo valida.
//
// Lo usan las rutas de app/api/: el catch-all (todo /api/v1) y la del reporte técnico de telemetría,
// que la API sirve fuera de /api/v1. Solo se ejecuta en el servidor.

// Si la API no responde en este tiempo, se corta la petición y se responde 504: el navegador no
// se queda esperando indefinidamente.
const API_TIMEOUT_MS = 15_000;

// Cabeceras que se copian en cada sentido; el resto (host, cookies…) no se reenvía.
// x-request-id: correlación de la telemetría (el navegador lo crea, la API lo registra y lo devuelve).
// x-cache: HIT o MISS de las cachés de la API (inventario y reporte), para `api_latency_recorded`.
const REQUEST_HEADERS = ["content-type", "accept", "authorization", "x-request-id"];
const RESPONSE_HEADERS = ["content-type", "content-disposition", "x-request-id", "x-cache"];

function errorResponse(status: number, code: string, message: string) {
  return Response.json({ error: { code, message } }, { status });
}

// Describe un fallo de red para el log: Node solo dice "fetch failed" y el motivo real (ECONNREFUSED,
// ENOTFOUND…) está en `cause`.
function describeFetchError(error: unknown): string {
  if (!(error instanceof Error)) return String(error);
  const cause = error.cause as { code?: string; message?: string } | undefined;
  const reason = cause?.code ?? cause?.message;
  return reason ? `${error.name}: ${error.message} (${reason})` : `${error.name}: ${error.message}`;
}

function pickHeaders(source: Headers, names: string[]) {
  const headers = new Headers();
  for (const name of names) {
    const value = source.get(name);
    if (value) headers.set(name, value);
  }
  return headers;
}

// Reenvía `request` a la URL que `buildTarget` construye a partir de API_BASE_URL (sin barra final).
// `route` es el método y la ruta sin query, solo para el log.
export async function proxyToApi(
  request: Request,
  buildTarget: (apiBaseUrl: string) => string,
  route: string,
): Promise<Response> {
  const apiBaseUrl = process.env.API_BASE_URL;
  if (!apiBaseUrl) {
    // El detalle de configuración queda en el log del servidor; el usuario recibe un mensaje genérico.
    console.error("[BFF] Falta la variable de entorno API_BASE_URL; defínela en .env.local (ver README).");
    return errorResponse(
      500,
      "api_not_configured",
      "El servicio no está disponible en este momento. Inténtalo más tarde y, si continúa, avisa al equipo técnico.",
    );
  }

  const target = buildTarget(apiBaseUrl.replace(/\/$/, ""));
  const hasBody = request.method !== "GET" && request.method !== "HEAD";

  let upstream: Response;
  try {
    upstream = await fetch(target, {
      method: request.method,
      headers: pickHeaders(request.headers, REQUEST_HEADERS),
      // El cuerpo se reenvía tal cual; content-type conserva el boundary del multipart.
      body: hasBody ? await request.arrayBuffer() : undefined,
      cache: "no-store",
      signal: AbortSignal.timeout(API_TIMEOUT_MS),
    });
  } catch (error) {
    // Se registran el método, la ruta (sin query) y el tipo de error; nunca cabeceras ni cuerpo,
    // que pueden llevar el token o datos personales.
    if (error instanceof DOMException && error.name === "TimeoutError") {
      console.error(`[BFF] ${route}: la API no respondió en ${API_TIMEOUT_MS / 1000} s.`);
      return errorResponse(504, "api_timeout", "La API tarda demasiado en responder. Inténtalo de nuevo en unos minutos.");
    }
    console.error(`[BFF] ${route}: no se pudo conectar con la API. ${describeFetchError(error)}`);
    return errorResponse(502, "api_unavailable", "La API de Brasaland no está disponible. Inténtalo más tarde.");
  }

  return new Response(upstream.body, {
    status: upstream.status,
    headers: pickHeaders(upstream.headers, RESPONSE_HEADERS),
  });
}

// Origen de la API (protocolo, host y puerto) a partir de API_BASE_URL, para las rutas que la API
// sirve fuera de /api/v1: http://api:8000/api/v1 → http://api:8000.
export function apiOrigin(apiBaseUrl: string): string {
  return new URL(apiBaseUrl).origin;
}
