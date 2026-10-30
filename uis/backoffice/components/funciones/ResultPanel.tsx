export interface Result {
  title: string;
  payload: unknown;
}

function describePayload(payload: unknown): string {
  if (Array.isArray(payload)) {
    return `Registros: ${payload.length}`;
  }

  if (payload && typeof payload === "object" && "valid" in payload && "errors" in payload) {
    const { valid, errors } = payload;
    return `Válido: ${valid ? "sí" : "no"} | Errores: ${Array.isArray(errors) ? errors.length : 0}`;
  }

  return "";
}

export default function ResultPanel({ result }: { result: Result }) {
  return (
    <section
      className="rounded-lg bg-gray-900 p-4 text-gray-100 lg:col-span-2"
      aria-labelledby="resultado-title"
      aria-live="polite"
    >
      <div className="mb-2 flex items-center justify-between gap-2">
        <h2 id="resultado-title" className="text-sm font-semibold">
          {result.title}
        </h2>
        <span className="text-xs text-gray-300">{describePayload(result.payload)}</span>
      </div>
      <pre className="max-h-80 overflow-auto whitespace-pre-wrap text-xs">
        {JSON.stringify(result.payload, null, 2)}
      </pre>
    </section>
  );
}
