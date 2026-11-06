import type { Metadata } from "next";
import "./globals.css";

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
        {children}
      </body>
    </html>
  );
}
