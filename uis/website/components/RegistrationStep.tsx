interface RegistrationStepProps {
  step: number;
  title: string;
  children: React.ReactNode;
}

export default function RegistrationStep({ step, title, children }: RegistrationStepProps) {
  const titleId = `step-${step}-title`;

  return (
    <div id={`step-${step}`} className="py-2" role="group" aria-labelledby={titleId}>
      <fieldset className="flex flex-col gap-4 py-4">
        <legend id={titleId} className="text-md text-center font-semibold text-gray-800">
          {title}
        </legend>
        <p className="text-sm text-gray-500">
          <span className="text-red-600">*</span> Campo obligatorio
        </p>
        {children}
      </fieldset>
    </div>
  );
}
