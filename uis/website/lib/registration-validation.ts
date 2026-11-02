import { getCityOptions, getFavoriteOptions } from "@/lib/locations";

export interface RegistrationValues {
  name: string;
  email: string;
  birthDate: string;
  country: string;
  city: string;
  favorite: string;
  phone: string;
  howFound: string;
  noRestrictions: boolean;
  vegan: boolean;
  glutenFree: boolean;
  other: boolean;
  offers: boolean;
  terms: boolean;
}

export type RegistrationField = keyof RegistrationValues;
export type RegistrationErrors = Partial<Record<RegistrationField, string>>;

export const TOTAL_STEPS = 3;

const STEP_FIELDS: Record<number, RegistrationField[]> = {
  1: ["name", "email", "birthDate"],
  2: ["country", "city", "favorite", "phone"],
  3: ["howFound", "noRestrictions", "terms"],
};

function isValidEmail(email: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email);
}

function isAdultOver18(value: string, today: Date) {
  const birth = new Date(value);
  if (Number.isNaN(birth.getTime())) return false;
  const threshold = new Date(today.getFullYear() - 18, today.getMonth(), today.getDate());
  return birth < threshold;
}

function hasAtLeastTwoWords(text: string) {
  return text.trim().split(/\s+/).filter(Boolean).length >= 2;
}

function isValidPhoneIntl(value: string) {
  return /^\+\d{8,15}$/.test(value);
}

// Devuelve el mensaje de error del campo, o "" si es válido.
export function validateField(
  field: RegistrationField,
  values: RegistrationValues,
  today: Date = new Date(),
): string {
  switch (field) {
    case "name":
      return hasAtLeastTwoWords(values.name)
        ? ""
        : "Ingresa tu nombre completo (nombre y apellido).";
    case "email": {
      const email = values.email.trim();
      if (!email) return "El correo es obligatorio.";
      return isValidEmail(email) ? "" : "Ingresa un email válido (ejemplo: nombre@correo.com).";
    }
    case "birthDate":
      if (!values.birthDate) return "La fecha de nacimiento es obligatoria.";
      return isAdultOver18(values.birthDate, today)
        ? ""
        : "Debes ser mayor de 18 años para registrarte en Brasa Points.";
    case "country":
      return values.country ? "" : "Selecciona tu país.";
    case "city": {
      if (!values.city) return "Selecciona tu ciudad.";
      const allowed = getCityOptions(values.country).map((city) => city.value);
      return allowed.includes(values.city) ? "" : "La ciudad no corresponde al país seleccionado.";
    }
    case "favorite": {
      if (!values.favorite) return "";
      const allowed = getFavoriteOptions(values.country, values.city).map((site) => site.value);
      return allowed.includes(values.favorite)
        ? ""
        : "La ubicación favorita no corresponde al país y ciudad seleccionados.";
    }
    case "phone": {
      const phone = values.phone.trim();
      if (!phone) return "El teléfono es obligatorio.";
      return isValidPhoneIntl(phone) ? "" : "Usa formato internacional: +[código país][10 dígitos].";
    }
    case "howFound":
      return values.howFound ? "" : "Selecciona una opción.";
    case "noRestrictions":
      return values.noRestrictions && (values.vegan || values.glutenFree || values.other)
        ? "No puedes seleccionar 'Sin restricciones' junto con otra preferencia."
        : "";
    case "terms":
      return values.terms ? "" : "Debes aceptar los términos del programa.";
    default:
      return "";
  }
}

// Valida los campos en orden y se detiene en el primero con error.
export function validateStep(step: number, values: RegistrationValues) {
  const errors: RegistrationErrors = {};

  for (const field of STEP_FIELDS[step]) {
    const message = validateField(field, values);
    errors[field] = message;
    if (message) return { valid: false, errors };
  }

  return { valid: true, errors };
}

// Solo sustituye el teléfono si está vacío o contiene únicamente un prefijo.
export function applyPhonePrefix(phone: string, prefix: string | undefined) {
  if (!prefix) return phone;
  const raw = phone.trim();
  return !raw || /^\+\d{1,4}$/.test(raw) ? prefix : phone;
}
