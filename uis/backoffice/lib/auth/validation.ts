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

// Comprobación básica; la definitiva la hace la API.
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function validateLogin(values: LoginValues): FieldErrors<LoginValues> {
  const errors: FieldErrors<LoginValues> = {};
  if (!values.email.trim()) errors.email = "Escribe tu email.";
  if (!values.password) errors.password = "Escribe tu contraseña.";
  return errors;
}

export function validateRegister(values: RegisterValues): FieldErrors<RegisterValues> {
  const errors: FieldErrors<RegisterValues> = {};
  const email = values.email.trim();

  if (!email) errors.email = "Escribe tu email.";
  else if (!EMAIL_PATTERN.test(email)) errors.email = "No es un email válido.";

  if (!values.password) {
    errors.password = "Escribe una contraseña.";
  } else if (values.password.length < MIN_PASSWORD_LENGTH) {
    errors.password = `La contraseña debe tener al menos ${MIN_PASSWORD_LENGTH} caracteres.`;
  } else if (new TextEncoder().encode(values.password).length > MAX_PASSWORD_BYTES) {
    errors.password = `La contraseña no puede superar ${MAX_PASSWORD_BYTES} bytes.`;
  }

  return errors;
}
