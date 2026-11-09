// Token JWT de la sesión, guardado en localStorage como exige el ticket AUTH-02.
// Solo funciona en el navegador: en el servidor no hay localStorage y no hay token.
// El navegador puede bloquear localStorage (datos del sitio bloqueados, algunos modos privados):
// entonces leerlo, escribirlo o incluso acceder a él lanza una excepción (SecurityError, QuotaExceededError).

const TOKEN_KEY = "brasaland.access_token";

// El evento "storage" solo avisa a las demás pestañas; este avisa a la pestaña actual.
const TOKEN_CHANGE_EVENT = "brasaland:token-change";

const STORAGE_BLOCKED_MESSAGE =
  "Tu navegador no permite guardar la sesión. Activa el almacenamiento de datos de este sitio (o sal del modo privado) e inténtalo de nuevo.";

// No se pudo guardar el token: el formulario que llama muestra este mensaje.
export class TokenStorageError extends Error {
  constructor() {
    super(STORAGE_BLOCKED_MESSAGE);
    this.name = "TokenStorageError";
  }
}

// localStorage, o null en el servidor o si el navegador no deja acceder a él.
function storage(): Storage | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage ?? null;
  } catch {
    return null;
  }
}

// Sin almacenamiento disponible no hay token: es lo mismo que no tener sesión.
export function getToken(): string | null {
  try {
    return storage()?.getItem(TOKEN_KEY) ?? null;
  } catch {
    return null;
  }
}

// Lanza TokenStorageError si el navegador no deja guardarlo: sin token no se puede mantener la sesión.
export function setToken(token: string): void {
  const store = storage();
  if (!store) throw new TokenStorageError();
  try {
    store.setItem(TOKEN_KEY, token);
  } catch {
    throw new TokenStorageError();
  }
  window.dispatchEvent(new Event(TOKEN_CHANGE_EVENT));
}

export function clearToken(): void {
  try {
    storage()?.removeItem(TOKEN_KEY);
  } catch {
    // Si el almacenamiento no está disponible, tampoco hay un token guardado que borrar.
  }
  if (typeof window !== "undefined") window.dispatchEvent(new Event(TOKEN_CHANGE_EVENT));
}

// De dónde viene el cambio. Cuando el token se borra en esta pestaña, quien lo borró
// (el cierre de sesión o el cliente común ante un 401) ya decide a dónde redirigir.
export type TokenChangeSource = "this-tab" | "other-tab";

// Avisa cuando el token cambia en esta pestaña o en otra. Devuelve la función para dejar de escuchar.
export function subscribeToToken(onChange: (source: TokenChangeSource) => void): () => void {
  if (!storage()) return () => {};

  function onStorage(event: StorageEvent) {
    // `key` es null cuando se vacía todo el localStorage.
    if (event.key === TOKEN_KEY || event.key === null) onChange("other-tab");
  }
  function onThisTab() {
    onChange("this-tab");
  }

  window.addEventListener("storage", onStorage);
  window.addEventListener(TOKEN_CHANGE_EVENT, onThisTab);
  return () => {
    window.removeEventListener("storage", onStorage);
    window.removeEventListener(TOKEN_CHANGE_EVENT, onThisTab);
  };
}
