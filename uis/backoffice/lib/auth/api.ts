import { apiJson, jsonBody } from "@/lib/api-client";
import type { CurrentUser, Profile, ProfileFields, RegisteredUser, RegisterInput, Token } from "@/types/auth";

// Login: un 401 aquí significa "credenciales incorrectas" y una cuenta desactivada se muestra
// en el formulario, así que no deben cerrar ninguna sesión ni redirigir.
export function login(email: string, password: string): Promise<Token> {
  return apiJson("/auth/login", {
    fallback: "no se pudo iniciar sesión",
    endSessionOnAuthError: false,
    ...jsonBody("POST", { email, password }),
  });
}

// Registro público (POST /users). Crea el usuario con rol `user` y su perfil inicial.
export function register(input: RegisterInput): Promise<RegisteredUser> {
  return apiJson("/users", {
    fallback: "no se pudo crear la cuenta",
    endSessionOnAuthError: false,
    ...jsonBody("POST", input),
  });
}

// Usuario de la sesión con su perfil. Un 401 cierra la sesión y redirige al login (lib/api-client.ts).
export function getCurrentUser(): Promise<CurrentUser> {
  return apiJson("/auth/me", { fallback: "no se pudo comprobar la sesión" });
}

// Actualiza el perfil propio (PUT /profiles/me). Solo cambian los campos enviados; null vacía el campo.
export function updateMyProfile(fields: Partial<ProfileFields>): Promise<Profile> {
  return apiJson("/profiles/me", {
    fallback: "no se pudo guardar el perfil",
    ...jsonBody("PUT", fields),
  });
}
