import RegistrationStep from "@/components/RegistrationStep";
import TextField from "@/components/TextField";
import type { RegistrationForm } from "@/hooks/useRegistrationForm";

export default function BasicInfoStep({ form }: { form: RegistrationForm }) {
  const { values, errors } = form;

  return (
    <RegistrationStep step={1} title="Datos básicos">
      <TextField
        id="name"
        label="Nombre completo"
        placeholder="Nombre completo"
        value={values.name}
        onChange={(value) => form.setField("name", value)}
        onBlur={() => form.validate("name")}
        error={errors.name}
        required
      />
      <TextField
        id="email"
        type="email"
        label="Correo electrónico"
        placeholder="correo@electronico.com"
        value={values.email}
        onChange={(value) => form.setField("email", value)}
        onBlur={() => form.validate("email")}
        error={errors.email}
        required
      />
      <TextField
        id="birth-year"
        type="date"
        label="Fecha de nacimiento"
        value={values.birthDate}
        onChange={(value) => form.setFieldAndValidate("birthDate", value)}
        error={errors.birthDate}
        required
        inline
      />
    </RegistrationStep>
  );
}
