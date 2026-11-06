// Token JWT de la sesión, guardado en localStorage como exige el ticket AUTH-02.
// Solo funciona en el navegador: en el servidor no hay localStorage y no hay token.

const TOKEN_KEY = "brasaland.access_token";

// El evento "storage" solo avisa a las demás pestañas; este avisa a la pestaña actual.
const TOKEN_CHANGE_EVENT = "brasaland:token-change";

function hasStorage(): boolean {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

export function getToken(): string | null {
  if (!hasStorage()) return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  if (!hasStorage()) return;
  window.localStorage.setItem(TOKEN_KEY, token);
  window.dispatchEvent(new Event(TOKEN_CHANGE_EVENT));
}

export function clearToken(): void {
  if (!hasStorage()) return;
  window.localStorage.removeItem(TOKEN_KEY);
  window.dispatchEvent(new Event(TOKEN_CHANGE_EVENT));
}

// De dónde viene el cambio. Cuando el token se borra en esta pestaña, quien lo borró
// (el cierre de sesión o el cliente común ante un 401) ya decide a dónde redirigir.
export type TokenChangeSource = "this-tab" | "other-tab";

// Avisa cuando el token cambia en esta pestaña o en otra. Devuelve la función para dejar de escuchar.
export function subscribeToToken(onChange: (source: TokenChangeSource) => void): () => void {
  if (!hasStorage()) return () => {};

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
