import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Brasaland: El sabor de la brasa, en cada bocado",
  description: "Cadena de restaurantes de carnes a la brasa en Colombia y Estados Unidos.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es" className="scroll-pt-22">
      <body className="bg-gray-100">{children}</body>
    </html>
  );
}
