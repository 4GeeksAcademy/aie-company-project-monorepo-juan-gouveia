import { useCallback, useEffect, useRef } from "react";
import { track } from "@/lib/telemetry";
import { onBeforeHide } from "@/lib/telemetry/lifecycle";
import { createFormSession, type FormExit, type FormId, type FormSession } from "@/lib/telemetry/navigation";

// Telemetría de un formulario (plan, §5.3), en un solo hook para todos:
// - fieldChanged(campo): llamarlo desde el setter del formulario (solo viaja el nombre del campo);
// - validationFailed(errores): cuando la validación del navegador bloquea el envío → `form_validation_failed`;
// - submitted(): tras un envío correcto (lo siguiente que se escriba es otro formulario);
// - al desmontarse sin enviar, o al ocultar/cerrar la pestaña, con algún campo cambiado → `form_abandoned`.
// `exit` es "navigation" para las vistas y "modal_closed" para los modales.
export function useFormTelemetry(formId: FormId, exit: Exclude<FormExit, "tab_closed"> = "navigation") {
  const session = useRef<FormSession | null>(null);
  session.current ??= createFormSession(formId);

  useEffect(() => {
    const current = session.current as FormSession;
    function abandon(how: FormExit) {
      const event = current.abandon(how, Date.now());
      if (event) track("form_abandoned", event);
    }
    const stopListening = onBeforeHide(() => abandon("tab_closed"));
    return () => {
      stopListening();
      abandon(exit);
    };
  }, [exit]);

  const fieldChanged = useCallback((field: string) => session.current?.change(field, Date.now()), []);

  const validationFailed = useCallback(
    (errors: Record<string, unknown>) => {
      const event = session.current?.invalid(errors, Date.now());
      if (event) track("form_validation_failed", event);
    },
    []
  );

  const submitted = useCallback(() => session.current?.succeed(), []);

  return { fieldChanged, validationFailed, submitted };
}
