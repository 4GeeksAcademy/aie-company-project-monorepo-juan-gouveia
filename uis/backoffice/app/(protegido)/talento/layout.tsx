import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Talent Pipeline Tracker",
  description: "Seguimiento de candidatos del proceso de selección de Brasaland.",
};

export default function TalentoLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
