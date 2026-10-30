import type { Metadata } from "next";
import Header from "@/components/Header";
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
      <body className="min-h-screen bg-gray-100">
        <Header />
        {children}
      </body>
    </html>
  );
}
