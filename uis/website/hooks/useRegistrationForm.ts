import { useState } from "react";
import { submitRegistration } from "@/lib/api";
import { getPhonePrefix } from "@/lib/locations";
import {
  applyPhonePrefix,
  TOTAL_STEPS,
  validateField,
  validateStep,
  type RegistrationErrors,
  type RegistrationField,
  type RegistrationValues,
} from "@/lib/registration-validation";

type SubmitStatus = "idle" | "submitting" | "success" | "error";
type DietaryField = "noRestrictions" | "vegan" | "glutenFree" | "other";

const INITIAL_VALUES: RegistrationValues = {
  name: "",
  email: "",
  birthDate: "",
  country: "",
  city: "",
  favorite: "",
  phone: "",
  howFound: "",
  noRestrictions: true,
  vegan: false,
  glutenFree: false,
  other: false,
  offers: false,
  terms: false,
};

export default function useRegistrationForm() {
  const [step, setStep] = useState(1);
  const [values, setValues] = useState<RegistrationValues>(INITIAL_VALUES);
  const [errors, setErrors] = useState<RegistrationErrors>({});
  const [status, setStatus] = useState<SubmitStatus>("idle");

  function setField<F extends RegistrationField>(field: F, value: RegistrationValues[F]) {
    setValues((current) => ({ ...current, [field]: value }));
  }

  function validate(field: RegistrationField, nextValues: RegistrationValues = values) {
    setErrors((current) => ({ ...current, [field]: validateField(field, nextValues) }));
  }

  function setFieldAndValidate<F extends RegistrationField>(
    field: F,
    value: RegistrationValues[F],
  ) {
    const nextValues = { ...values, [field]: value };
    setValues(nextValues);
    validate(field, nextValues);
  }

  function changeCountry(country: string) {
    const nextValues = {
      ...values,
      country,
      city: "",
      favorite: "",
      phone: applyPhonePrefix(values.phone, getPhonePrefix(country)),
    };
    setValues(nextValues);
    setErrors((current) => ({
      ...current,
      country: validateField("country", nextValues),
      city: "",
      favorite: "",
    }));
  }

  function changeCity(city: string) {
    const nextValues = { ...values, city, favorite: "" };
    setValues(nextValues);
    setErrors((current) => ({
      ...current,
      city: validateField("city", nextValues),
      favorite: "",
    }));
  }

  // "Sin restricciones" excluye a las demás opciones, y viceversa.
  function changeDietary(field: DietaryField, checked: boolean) {
    const nextValues = { ...values, [field]: checked };

    if (checked && field === "noRestrictions") {
      nextValues.vegan = false;
      nextValues.glutenFree = false;
      nextValues.other = false;
    } else if (checked) {
      nextValues.noRestrictions = false;
    }

    setValues(nextValues);
    validate("noRestrictions", nextValues);
  }

  function nextStep() {
    const result = validateStep(step, values);
    setErrors((current) => ({ ...current, ...result.errors }));
    if (result.valid) setStep(Math.min(step + 1, TOTAL_STEPS));
  }

  function previousStep() {
    setStep(Math.max(step - 1, 1));
  }

  async function submit() {
    for (let current = 1; current <= TOTAL_STEPS; current += 1) {
      const result = validateStep(current, values);
      setErrors((previous) => ({ ...previous, ...result.errors }));
      if (!result.valid) {
        setStep(current);
        return;
      }
    }

    setStatus("submitting");
    try {
      await submitRegistration(values);
      setStatus("success");
    } catch {
      setStatus("error");
    }
  }

  return {
    step,
    values,
    errors,
    status,
    setField,
    setFieldAndValidate,
    validate,
    changeCountry,
    changeCity,
    changeDietary,
    nextStep,
    previousStep,
    submit,
  };
}

export type RegistrationForm = ReturnType<typeof useRegistrationForm>;
