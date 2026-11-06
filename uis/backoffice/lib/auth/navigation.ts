// Rutas del login y del destino tras autenticarse (?next=).

export const LOGIN_PATH = "/login";
export const HOME_PATH = "/";

// Por qué se envía al usuario al login; el login muestra un mensaje según el motivo.
export type LoginReason = "expired" | "inactive";

// Solo se admiten rutas internas, para que ?next= no pueda enviar al usuario a otro sitio.
// "//dominio" y "/\dominio" los interpreta el navegador como URL de otro origen.
export function safeNext(next: string | null | undefined): string {
  if (!next || !next.startsWith("/") || next.startsWith("//") || next.startsWith("/\\")) {
    return HOME_PATH;
  }
  return next;
}

export function loginUrl(next?: string, reason?: LoginReason): string {
  const params = new URLSearchParams();
  if (next && safeNext(next) !== HOME_PATH) params.set("next", next);
  if (reason) params.set("reason", reason);
  const query = params.toString();
  return query ? `${LOGIN_PATH}?${query}` : LOGIN_PATH;
}

// Ruta actual del navegador (con su query), para volver a ella tras el login.
export function currentPath(): string {
  if (typeof window === "undefined") return HOME_PATH;
  return `${window.location.pathname}${window.location.search}`;
}
