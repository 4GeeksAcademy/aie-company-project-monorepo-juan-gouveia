import { ApiError } from "@/lib/api-client";
import { TokenStorageError } from "@/lib/auth/token";

// Texto que ve el usuario para cualquier error capturado. Solo se muestra el mensaje de los errores
// que ya están pensados para el usuario: los de la API (ApiError, con su texto en español) y el del
// almacenamiento de la sesión. Cualquier otro (TypeError, SyntaxError, errores de librerías…) puede
// traer un texto técnico o en inglés, así que se sustituye por `fallback`, que debe decir qué falló
// y, si se puede, qué hacer.
export function toUserMessage(err: unknown, fallback: string): string {
  if (err instanceof ApiError || err instanceof TokenStorageError) return err.message;
  return fallback;
}
