import { apiJson, jsonBody } from "@/lib/api-client";
import type {
  CurrentUser,
  PasswordChanged,
  Profile,
  ProfileFields,
  RegisteredUser,
  RegisterInput,
  Token,
} from "@/types/auth";

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

// --- Restablecimiento de contraseña (AUTH-03) ---------------------------------------------------
// Rutas públicas: quien olvidó la contraseña no tiene sesión, así que un error no debe cerrar nada.

// POST /auth/forgot-password: responde siempre 200 con el mismo mensaje, exista o no el email.
export function forgotPassword(email: string): Promise<{ message: string }> {
  return apiJson("/auth/forgot-password", {
    fallback: "no se pudo enviar la solicitud",
    endSessionOnAuthError: false,
    ...jsonBody("POST", { email }),
  });
}

// POST /auth/reset-password: 400 si el enlace no es válido, caducó o ya se usó.
export function resetPassword(token: string, newPassword: string): Promise<{ message: string }> {
  return apiJson("/auth/reset-password", {
    fallback: "no se pudo restablecer la contraseña",
    endSessionOnAuthError: false,
    ...jsonBody("POST", { token, new_password: newPassword }),
  });
}

// POST /auth/reset-password/validate: comprueba el enlace sin usarlo (400 con el motivo si no sirve).
// El token va en el cuerpo, no en la URL de la API, para que no quede en los logs de acceso.
export function validateResetToken(token: string): Promise<{ message: string }> {
  return apiJson("/auth/reset-password/validate", {
    fallback: "no se pudo comprobar el enlace",
    endSessionOnAuthError: false,
    ...jsonBody("POST", { token }),
  });
}

// --- Cambio de contraseña con sesión (AUTH-03) -------------------------------------------------

// POST /auth/change-password: 400 si la contraseña actual no es correcta. Con éxito, las sesiones
// anteriores dejan de valer y la respuesta trae el token que las sustituye. Un 401 (sesión caducada
// o cerrada) sí cierra la sesión, como en el resto de la zona protegida.
export function changePassword(currentPassword: string, newPassword: string): Promise<PasswordChanged> {
  return apiJson("/auth/change-password", {
    fallback: "no se pudo cambiar la contraseña",
    ...jsonBody("POST", { current_password: currentPassword, new_password: newPassword }),
  });
}
