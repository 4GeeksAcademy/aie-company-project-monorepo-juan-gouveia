import type { Metadata } from "next";
import "./globals.css";
import TelemetryRoot from "@/components/telemetry/TelemetryRoot";

export const metadata: Metadata = {
  title: {
    default: "Backoffice | Brasaland",
    template: "%s | Brasaland",
  },
  description: "Herramientas internas del equipo de Brasaland.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es">
      {/* La cabecera la pone el layout de cada grupo: (protegido) con navegación y (publico) sin ella. */}
      <body className="min-h-screen bg-gray-100">
        {/* Telemetría transversal: vistas, errores de JavaScript y Web Vitals (no dibuja nada). */}
        <TelemetryRoot />
        {children}
      </body>
    </html>
  );
}
