import CheckboxField from "@/components/CheckboxField";
import RegistrationStep from "@/components/RegistrationStep";
import SelectField from "@/components/SelectField";
import type { RegistrationForm } from "@/hooks/useRegistrationForm";

const HOW_FOUND_OPTIONS = [
  { value: "redes-sociales", label: "Redes sociales" },
  { value: "recomendacion", label: "Recomendación" },
  { value: "pasando-por-el-local", label: "Pasando por el local" },
  { value: "busqueda-en-internet", label: "Búsqueda en internet" },
  { value: "otro", label: "Otro" },
];

export default function AboutYouStep({ form }: { form: RegistrationForm }) {
  const { values, errors } = form;

  return (
    <RegistrationStep step={3} title="Sobre ti">
      <p className="text-gray-700">Selecciona tus restricciones alimenticias</p>
      <div className="grid grid-cols-2 gap-4">
        <CheckboxField
          id="sin-restricciones"
          label="Sin restricciones"
          checked={values.noRestrictions}
          onChange={(checked) => form.changeDietary("noRestrictions", checked)}
          error={errors.noRestrictions}
        />
        <CheckboxField
          id="vegano"
          label="Vegano"
          checked={values.vegan}
          onChange={(checked) => form.changeDietary("vegan", checked)}
        />
        <CheckboxField
          id="sin-gluten"
          label="Sin gluten"
          checked={values.glutenFree}
          onChange={(checked) => form.changeDietary("glutenFree", checked)}
        />
        <CheckboxField
          id="otros"
          label="Otros"
          checked={values.other}
          onChange={(checked) => form.changeDietary("other", checked)}
        />
      </div>

      <div className="flex flex-col gap-4">
        <SelectField
          id="como-nos-conociste"
          label="¿Cómo nos conociste?"
          placeholder="Selecciona una opción"
          options={HOW_FOUND_OPTIONS}
          value={values.howFound}
          onChange={(value) => form.setFieldAndValidate("howFound", value)}
          error={errors.howFound}
          required
        />
        <CheckboxField
          id="ofertas-email"
          label="Quiero recibir ofertas por email"
          checked={values.offers}
          onChange={(checked) => form.setField("offers", checked)}
        />
        <CheckboxField
          id="acepto-terminos"
          label="Acepto términos del programa"
          checked={values.terms}
          onChange={(checked) => form.setFieldAndValidate("terms", checked)}
          error={errors.terms}
          required
        />
      </div>
    </RegistrationStep>
  );
}
