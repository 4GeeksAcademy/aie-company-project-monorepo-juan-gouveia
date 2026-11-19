import { apiJson, apiJsonWithRequestId, jsonBody } from "@/lib/api-client";
import {
  markLoginSucceeded,
  trackLoginFailed,
  trackPasswordChanged,
  trackPasswordResetCompleted,
  trackUserRegistered,
} from "@/lib/telemetry/auth-events";
import type {
  CurrentUser,
  PasswordChanged,
  Profile,
  ProfileFields,
  RegisteredUser,
  RegisterInput,
  Token,
} from "@/types/auth";

// Telemetría de autenticación (lib/telemetry/auth-events.ts): se emite aquí y en SessionProvider,
// nunca en cada página, y sin el email ni la contraseña escritos.

// Login: un 401 aquí significa "credenciales incorrectas" y una cuenta desactivada se muestra
// en el formulario, así que no deben cerrar ninguna sesión ni redirigir.
// Telemetría: `login_failed` con el motivo; `login_succeeded` al validar la sesión (necesita el rol).
export async function login(email: string, password: string): Promise<Token> {
  try {
    const { data, requestId } = await apiJsonWithRequestId<Token>("/auth/login", {
      fallback: "no se pudo iniciar sesión",
      endSessionOnAuthError: false,
      ...jsonBody("POST", { email, password }),
    });
    markLoginSucceeded(requestId);
    return data;
  } catch (err) {
    trackLoginFailed(err);
    throw err;
  }
}

// Registro público (POST /users). Crea el usuario con rol `user` y su perfil inicial.
// Telemetría: `user_registered` con el id de la cuenta nueva.
export async function register(input: RegisterInput): Promise<RegisteredUser> {
  const { data, requestId } = await apiJsonWithRequestId<RegisteredUser>("/users", {
    fallback: "no se pudo crear la cuenta",
    endSessionOnAuthError: false,
    ...jsonBody("POST", input),
  });
  trackUserRegistered(data.id, requestId);
  return data;
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
// Telemetría: `password_reset_completed` (el rechazo del enlace lo emite api-events.ts).
export async function resetPassword(token: string, newPassword: string): Promise<{ message: string }> {
  const { data, requestId } = await apiJsonWithRequestId<{ message: string }>("/auth/reset-password", {
    fallback: "no se pudo restablecer la contraseña",
    endSessionOnAuthError: false,
    ...jsonBody("POST", { token, new_password: newPassword }),
  });
  trackPasswordResetCompleted(token, requestId);
  return data;
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
// Telemetría: `password_changed`.
export async function changePassword(currentPassword: string, newPassword: string): Promise<PasswordChanged> {
  const { data, requestId } = await apiJsonWithRequestId<PasswordChanged>("/auth/change-password", {
    fallback: "no se pudo cambiar la contraseña",
    ...jsonBody("POST", { current_password: currentPassword, new_password: newPassword }),
  });
  trackPasswordChanged(requestId);
  return data;
}
