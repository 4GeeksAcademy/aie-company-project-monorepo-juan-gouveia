import type { Metadata } from "next";
import JsonLd from "@/components/JsonLd";
import RegistrationForm from "@/components/RegistrationForm";
import RegistrationHeader from "@/components/RegistrationHeader";
import SiteFooter from "@/components/SiteFooter";

const TITLE = "Brasaland: Registrate en Brasa Points";

export const metadata: Metadata = {
  title: TITLE,
};

export default function RegistroPage() {
  return (
    <>
      <JsonLd pageName={TITLE} />
      <RegistrationHeader />
      <main>
        <section className="mx-auto max-w-6xl px-3 mt-12 md:px-4 lg:px-8">
          <div className="flex flex-col items-center justify-center gap-4 py-12 text-center">
            <h1 className="text-3xl font-bold text-gray-800 sm:text-4xl">
              ¡Bienvenido a Brasa Points!
            </h1>
            <p className="text-lg text-gray-600 sm:text-xl">
              Regístrate y empieza a disfrutar de los beneficios de ser parte de nuestra familia.
            </p>
          </div>
        </section>

        {/* Registro multi-paso */}
        <section className="bg-white rounded-lg p-4 shadow-md" aria-labelledby="registro-title">
          <h2 id="registro-title" className="sr-only">
            Formulario de registro Brasa Points
          </h2>
          <RegistrationForm />
        </section>
      </main>
      <SiteFooter showSocialLinks={false} />
    </>
  );
}
