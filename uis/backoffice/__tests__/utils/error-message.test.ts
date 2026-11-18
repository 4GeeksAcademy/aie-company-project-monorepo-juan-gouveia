// Texto que ve el usuario para cualquier error capturado (lib/error-message.ts): solo se muestran
// los mensajes pensados para el usuario; cualquier otro se sustituye por el texto de respaldo.
import { ApiError } from "@/lib/api-client";
import { TokenStorageError } from "@/lib/auth/token";
import { toUserMessage } from "@/lib/error-message";

const FALLBACK = "No se pudo cargar el directorio. Inténtalo de nuevo.";

describe("toUserMessage", () => {
  it("muestra el mensaje en español de un error de la API", () => {
    const error = new ApiError("Ya existe un proveedor llamado «Carnes del Valle».", 409, "duplicate_supplier");

    expect(toUserMessage(error, FALLBACK)).toBe("Ya existe un proveedor llamado «Carnes del Valle».");
  });

  it("muestra el mensaje del almacenamiento bloqueado de la sesión", () => {
    expect(toUserMessage(new TokenStorageError(), FALLBACK)).toMatch(/no permite guardar la sesión/);
  });

  it.each([
    ["TypeError de red", new TypeError("Failed to fetch")],
    ["SyntaxError de JSON", new SyntaxError("Unexpected token < in JSON at position 0")],
    ["Error genérico", new Error("Cannot read properties of undefined (reading 'map')")],
    ["un texto lanzado", "boom"],
    ["undefined", undefined],
  ])("nunca muestra el texto técnico de %s", (_label, error) => {
    expect(toUserMessage(error, FALLBACK)).toBe(FALLBACK);
  });
});
