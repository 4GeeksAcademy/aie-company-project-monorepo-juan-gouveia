import type { Metadata } from "next";
import Image from "next/image";
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
        <header className="border-b border-red-200 bg-white">
          <div className="mx-auto flex h-auto items-center px-3 py-2 md:px-4 lg:max-w-6xl lg:px-8">
            <Image
              src="/logo-brasaland.png"
              alt="Logo Brasaland"
              width={160}
              height={72}
              className="h-18 w-auto"
              priority
            />
          </div>
        </header>

        {children}
      </body>
    </html>
  );
}
