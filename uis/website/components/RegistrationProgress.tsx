const STEP_LABELS = ["Datos básicos", "Ubicación", "Sobre ti"];

export default function RegistrationProgress({ step }: { step: number }) {
  return (
    <div className="py-4">
      <ol className="grid grid-cols-3 gap-4" aria-label="Progreso del registro">
        {STEP_LABELS.map((label, index) => {
          const number = index + 1;
          const reached = number <= step;

          return (
            <li
              key={label}
              className="flex flex-col items-center gap-2 text-center"
              aria-current={number === step ? "step" : undefined}
            >
              <span
                className={`flex h-8 w-8 items-center justify-center rounded-full text-sm font-semibold ${
                  reached ? "bg-red-600 text-white" : "bg-gray-200 text-gray-700"
                }`}
              >
                {number}
              </span>
              <span
                className={`text-sm font-medium ${reached ? "text-gray-800" : "text-gray-500"}`}
              >
                {label}
              </span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
