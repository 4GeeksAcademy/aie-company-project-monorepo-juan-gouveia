// Comprobaciones del formulario antes de llamar a la API. La API valida igualmente
// y sus errores por campo (`details`) se muestran junto a cada campo.

// Mismos límites que la API (services/brasaland-api: users/models.py y profiles/models.py).
export const MIN_PASSWORD_LENGTH = 8;
export const MAX_PASSWORD_BYTES = 72;
export const MAX_NAME_LENGTH = 120;
export const MAX_PHONE_LENGTH = 30;
export const MAX_ADDRESS_LENGTH = 200;

export interface LoginValues {
  email: string;
  password: string;
}

export interface RegisterValues extends LoginValues {
  name: string;
  phone: string;
  address: string;
}

export type FieldErrors<T> = Partial<Record<keyof T, string>>;

// Errores que se muestran: los de la validación local y, encima, los de la API. Solo cuentan los
// errores de la API que tienen texto: al editar un campo, su error de la API queda en undefined y
// no debe tapar el error local de ese campo.
export function mergeFieldErrors<T>(local: FieldErrors<T>, api: FieldErrors<T>): FieldErrors<T> {
  const merged: FieldErrors<T> = { ...local };
  for (const key of Object.keys(api) as (keyof T)[]) {
    if (api[key]) merged[key] = api[key];
  }
  return merged;
}

// Comprobación básica; la definitiva la hace la API.
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function validateLogin(values: LoginValues): FieldErrors<LoginValues> {
  const errors: FieldErrors<LoginValues> = {};
  if (!values.email.trim()) errors.email = "Escribe tu email.";
  if (!values.password) errors.password = "Escribe tu contraseña.";
  return errors;
}

// Error del email, o null si es válido.
export function emailError(value: string): string | null {
  const email = value.trim();
  if (!email) return "Escribe tu email.";
  if (!EMAIL_PATTERN.test(email)) return "No es un email válido.";
  return null;
}

// Mismas reglas que la API para una contraseña nueva (registro, restablecimiento y cambio).
export function passwordError(password: string): string | null {
  if (!password) return "Escribe una contraseña.";
  if (password.length < MIN_PASSWORD_LENGTH) {
    return `La contraseña debe tener al menos ${MIN_PASSWORD_LENGTH} caracteres.`;
  }
  if (new TextEncoder().encode(password).length > MAX_PASSWORD_BYTES) {
    return `La contraseña no puede superar ${MAX_PASSWORD_BYTES} bytes.`;
  }
  return null;
}

export function validateRegister(values: RegisterValues): FieldErrors<RegisterValues> {
  const errors: FieldErrors<RegisterValues> = {};
  const email = emailError(values.email);
  if (email) errors.email = email;
  const password = passwordError(values.password);
  if (password) errors.password = password;
  return errors;
}

// Contraseña nueva con confirmación (restablecimiento y cambio, AUTH-03). Se comprueba que
// coinciden antes de llamar a la API, como pide el ticket.
export interface NewPasswordValues {
  newPassword: string;
  confirmPassword: string;
}

export function validateNewPassword(values: NewPasswordValues): FieldErrors<NewPasswordValues> {
  const errors: FieldErrors<NewPasswordValues> = {};
  const password = passwordError(values.newPassword);
  if (password) errors.newPassword = password;
  if (!values.confirmPassword) errors.confirmPassword = "Repite la contraseña nueva.";
  else if (values.confirmPassword !== values.newPassword) errors.confirmPassword = "Las contraseñas no coinciden.";
  return errors;
}

// Cambio de contraseña con sesión: la actual, más la nueva con su confirmación.
export interface ChangePasswordValues extends NewPasswordValues {
  currentPassword: string;
}

export function validateChangePassword(values: ChangePasswordValues): FieldErrors<ChangePasswordValues> {
  const errors: FieldErrors<ChangePasswordValues> = validateNewPassword(values);
  if (!values.currentPassword) errors.currentPassword = "Escribe tu contraseña actual.";
  return errors;
}
