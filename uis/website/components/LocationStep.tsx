import RegistrationStep from "@/components/RegistrationStep";
import SelectField from "@/components/SelectField";
import TextField from "@/components/TextField";
import type { RegistrationForm } from "@/hooks/useRegistrationForm";
import { getCityOptions, getCountryOptions, getFavoriteOptions } from "@/lib/locations";

export default function LocationStep({ form }: { form: RegistrationForm }) {
  const { values, errors } = form;
  const cities = getCityOptions(values.country);
  const favorites = getFavoriteOptions(values.country, values.city);

  return (
    <RegistrationStep step={2} title="Sobre tu ubicación">
      <SelectField
        id="pais"
        label="País"
        placeholder="Selecciona un país"
        options={getCountryOptions()}
        value={values.country}
        onChange={form.changeCountry}
        error={errors.country}
        required
      />
      <SelectField
        id="ciudad"
        label="Ciudad"
        placeholder="Selecciona tu ciudad"
        options={cities}
        value={values.city}
        onChange={form.changeCity}
        disabled={cities.length === 0}
        error={errors.city}
        required
      />
      <SelectField
        id="ubicacion-favorita"
        label="Brasaland favorito"
        placeholder="Selecciona tu Brasaland favorito"
        options={favorites}
        value={values.favorite}
        onChange={(value) => form.setFieldAndValidate("favorite", value)}
        disabled={favorites.length === 0}
        error={errors.favorite}
      />
      <TextField
        id="telefono"
        type="tel"
        label="Número telefónico"
        placeholder="+573001234567"
        value={values.phone}
        onChange={(value) => form.setField("phone", value)}
        onBlur={() => form.validate("phone")}
        error={errors.phone}
        required
      />
    </RegistrationStep>
  );
}
