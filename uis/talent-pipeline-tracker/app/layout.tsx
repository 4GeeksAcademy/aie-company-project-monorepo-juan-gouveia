import type { Metadata } from "next";
import Header from "@/components/Header";
import "./globals.css";

export const metadata: Metadata = {
  title: "Talent Pipeline Tracker | Brasaland",
  description: "Seguimiento de candidatos del proceso de selección de Brasaland.",
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
