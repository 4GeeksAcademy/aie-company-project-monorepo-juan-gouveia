import type { RegistrationValues } from "@/lib/registration-validation";

// Envío simulado: no guarda ni transmite datos. Cuando exista el endpoint en FastAPI,
// solo hay que sustituir este cuerpo por la llamada real.
export async function submitRegistration(values: RegistrationValues): Promise<void> {
  void values;
}
