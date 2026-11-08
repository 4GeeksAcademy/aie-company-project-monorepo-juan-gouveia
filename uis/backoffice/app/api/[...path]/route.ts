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
    return errorResponse(500, "api_not_configured", "Falta la variable API_BASE_URL en el backoffice.");
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
    if (error instanceof DOMException && error.name === "TimeoutError") {
      return errorResponse(504, "api_timeout", "La API tarda demasiado en responder. Inténtalo de nuevo en unos minutos.");
    }
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
