import type { Metadata } from "next";
import ErrorScreen from "@/components/ErrorScreen";
import RegistrationHeader from "@/components/RegistrationHeader";

export const metadata: Metadata = {
  title: "Brasaland: página no encontrada",
};

// Rutas que no existen.
export default function NotFound() {
  return (
    <>
      <RegistrationHeader />
      {/* La cabecera es fija: el contenido empieza por debajo. */}
      <main className="pt-24">
        <ErrorScreen
          title="Página no encontrada"
          message="La página que buscas no existe o cambió de dirección. Desde la página principal puedes ver nuestros locales y Brasa Points."
        />
      </main>
    </>
  );
}
