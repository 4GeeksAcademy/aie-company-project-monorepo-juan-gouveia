// Formato común de los errores de la API de Brasaland: { error: { code, message, details? } },
// con el mensaje en español. Los 422 de validación incluyen `details` por campo.

export interface ApiFieldError {
  field: string;
  message: string;
}

export interface ApiErrorBody {
  error: { code: string; message: string; details?: ApiFieldError[] };
}
