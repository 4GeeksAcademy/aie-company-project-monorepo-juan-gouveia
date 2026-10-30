"use client";

import Link from "next/link";
import AboutYouStep from "@/components/AboutYouStep";
import BasicInfoStep from "@/components/BasicInfoStep";
import LocationStep from "@/components/LocationStep";
import RegistrationProgress from "@/components/RegistrationProgress";
import useRegistrationForm from "@/hooks/useRegistrationForm";
import { TOTAL_STEPS } from "@/lib/registration-validation";

const NAV_BUTTON_CLASS = "w-full rounded bg-red-600 px-4 py-2 text-white hover:bg-red-700";

// Sin esto, el campo pierde el foco al pulsar, su error desaparece, el botón se desplaza y el clic se pierde.
function keepFieldFocus(event: React.MouseEvent) {
  event.preventDefault();
}

export default function RegistrationForm() {
  const form = useRegistrationForm();
  const { step, status } = form;

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (step < TOTAL_STEPS) {
      form.nextStep();
    } else {
      form.submit();
    }
  }

  if (status === "success") {
    return (
      <div role="status" className="mx-auto max-w-6xl px-3 py-8 text-center md:px-4 lg:px-8">
        <p className="mb-4 text-lg font-semibold text-gray-800">
          ¡Gracias por registrarte en Brasa Points!
        </p>
        <Link href="/" className="text-red-600 underline hover:text-red-700">
          Volver al inicio
        </Link>
      </div>
    );
  }

  return (
    <form
      id="registration-form"
      className="mx-auto max-w-6xl px-3 md:px-4 lg:px-8"
      onSubmit={handleSubmit}
      noValidate
    >
      <RegistrationProgress step={step} />

      {step === 1 && <BasicInfoStep form={form} />}
      {step === 2 && <LocationStep form={form} />}
      {step === 3 && <AboutYouStep form={form} />}

      {status === "error" && (
        <p role="alert" className="mb-2 text-sm text-red-600">
          No se pudo completar el registro. Inténtalo de nuevo.
        </p>
      )}

      <div className="grid grid-cols-2 gap-4 py-2 md:grid-cols-2">
        {step > 1 && (
          <button
            id="prev-step-btn"
            type="button"
            onClick={form.previousStep}
            onMouseDown={keepFieldFocus}
            className={NAV_BUTTON_CLASS}
          >
            Anterior
          </button>
        )}
        {/* Ambos son "submit" para que Enter funcione en cada paso; handleSubmit decide qué hacer. */}
        {step < TOTAL_STEPS ? (
          <button
            key="next"
            id="next-step-btn"
            type="submit"
            onMouseDown={keepFieldFocus}
            className={`col-start-2 ${NAV_BUTTON_CLASS}`}
          >
            Siguiente
          </button>
        ) : (
          <button
            key="submit"
            id="submit-step-btn"
            type="submit"
            disabled={status === "submitting"}
            className={`col-start-2 ${NAV_BUTTON_CLASS}`}
          >
            Confirmar
          </button>
        )}
      </div>
    </form>
  );
}
