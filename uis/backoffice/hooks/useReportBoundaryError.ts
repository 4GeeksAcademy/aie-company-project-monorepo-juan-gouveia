import { useEffect } from "react";
import { captureFrontendError } from "@/lib/telemetry/errors";

// Telemetría de las pantallas de error de Next (`error.tsx` y `global-error.tsx`): emite
// `frontend_error_captured` con `source: "error_boundary"` una vez por error mostrado. El mensaje se
// sanea antes de salir (lib/telemetry/errors.ts); la pantalla sigue sin mostrarlo al usuario.
export function useReportBoundaryError(error: Error): void {
  useEffect(() => {
    captureFrontendError(error, "error_boundary");
  }, [error]);
}
