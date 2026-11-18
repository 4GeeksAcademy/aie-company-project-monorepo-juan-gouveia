/**
 * @jest-environment jsdom
 */
// Token de la sesión en localStorage (lib/auth/token.ts), con un navegador simulado (jsdom).
// El navegador puede bloquear localStorage: entonces no hay sesión, pero nada debe romperse.
import { clearToken, getToken, setToken, subscribeToToken, TokenStorageError } from "@/lib/auth/token";

const TOKEN_KEY = "brasaland.access_token";

afterEach(() => {
  jest.restoreAllMocks();
  window.localStorage.clear();
});

function blockStorage(method: "getItem" | "setItem" | "removeItem") {
  jest.spyOn(Storage.prototype, method).mockImplementation(() => {
    throw new DOMException("bloqueado", "SecurityError");
  });
}

describe("getToken y setToken", () => {
  it("guarda el token en localStorage y lo recupera", () => {
    setToken("jwt-de-prueba");

    expect(window.localStorage.getItem(TOKEN_KEY)).toBe("jwt-de-prueba");
    expect(getToken()).toBe("jwt-de-prueba");
  });

  it("sin token guardado no hay sesión", () => {
    expect(getToken()).toBeNull();
  });

  it("si el navegador bloquea la lectura, se trata como sin sesión", () => {
    blockStorage("getItem");

    expect(getToken()).toBeNull();
  });

  it("si el navegador bloquea la escritura, lanza TokenStorageError con un mensaje para el usuario", () => {
    blockStorage("setItem");

    expect(() => setToken("jwt-de-prueba")).toThrow(TokenStorageError);
    expect(() => setToken("jwt-de-prueba")).toThrow(/no permite guardar la sesión/);
  });
});

describe("clearToken", () => {
  it("borra el token", () => {
    setToken("jwt-de-prueba");

    clearToken();

    expect(getToken()).toBeNull();
  });

  it("no falla si el navegador bloquea el borrado", () => {
    blockStorage("removeItem");

    expect(() => clearToken()).not.toThrow();
  });
});

describe("subscribeToToken", () => {
  it("avisa de los cambios en esta pestaña y deja de avisar al cancelar", () => {
    const onChange = jest.fn();
    const unsubscribe = subscribeToToken(onChange);

    setToken("jwt-de-prueba");
    clearToken();
    unsubscribe();
    setToken("otro-jwt");

    expect(onChange.mock.calls).toEqual([["this-tab"], ["this-tab"]]);
  });

  it("avisa de los cambios del token en otra pestaña e ignora otras claves", () => {
    const onChange = jest.fn();
    const unsubscribe = subscribeToToken(onChange);

    window.dispatchEvent(new StorageEvent("storage", { key: "otra-clave" }));
    window.dispatchEvent(new StorageEvent("storage", { key: TOKEN_KEY }));
    window.dispatchEvent(new StorageEvent("storage", { key: null })); // localStorage.clear() en otra pestaña
    unsubscribe();

    expect(onChange.mock.calls).toEqual([["other-tab"], ["other-tab"]]);
  });
});
