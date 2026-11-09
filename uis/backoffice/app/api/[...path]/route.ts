// Intermediario (Backend for Frontend) entre el navegador y la API de Brasaland.
// Solo reenvía la petición: no aplica reglas de negocio ni decide permisos (propuesta 5.2).
// Así la URL de la API es una variable de servidor y el navegador no necesita CORS.
// El token JWT lo envía el navegador en Authorization (ticket AUTH-02) y se reenvía tal cual;
// la API es quien lo valida.

const API_BASE_URL = process.env.API_BASE_URL;

// Si la API no responde en este tiempo, se corta la petición y se responde 504: el navegador no
// se queda esperando indefinidamente.
const API_TIMEOUT_MS = 15_000;

// Cabeceras que se copian en cada sentido; el resto (host, cookies…) no se reenvía.
const REQUEST_HEADERS = ["content-type", "accept", "authorization"];
const RESPONSE_HEADERS = ["content-type", "content-disposition"];

interface RouteContext {
  params: Promise<{ path: string[] }>;
}

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

async function forward(request: Request, { params }: RouteContext) {
  if (!API_BASE_URL) {
    // El detalle de configuración queda en el log del servidor; el usuario recibe un mensaje genérico.
    console.error("[BFF] Falta la variable de entorno API_BASE_URL; defínela en .env.local (ver README).");
    return errorResponse(
      500,
      "api_not_configured",
      "El servicio no está disponible en este momento. Inténtalo más tarde y, si continúa, avisa al equipo técnico.",
    );
  }

  const { path } = await params;
  const { search } = new URL(request.url);
  const target = `${API_BASE_URL.replace(/\/$/, "")}/${path.map(encodeURIComponent).join("/")}${search}`;
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
    const route = `${request.method} /${path.join("/")}`;
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

export const GET = forward;
export const POST = forward;
export const PUT = forward;
export const PATCH = forward;
export const DELETE = forward;
