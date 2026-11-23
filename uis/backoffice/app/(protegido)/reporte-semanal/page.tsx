import type { Metadata } from "next";
import WeeklyReportPanel from "@/components/reporte-semanal/WeeklyReportPanel";

export const metadata: Metadata = {
  title: "Reporte semanal de costo y merma",
  description: "Costo de compra, costo de merma, ratio de merma, quiebres de stock y alertas de precio de cada local, por semana.",
};

export default function WeeklyReportPage() {
  return (
    <main className="px-3 py-6 md:px-4 lg:mx-auto lg:max-w-6xl lg:px-8">
      <h1 className="mb-2 text-xl font-semibold text-red-700 md:text-2xl lg:text-3xl">
        Reporte Semanal de Costo y Merma por Local
      </h1>
      <p className="mb-6 text-sm text-black md:text-base">
        Cuánto compró y cuánto perdió por merma cada uno de los 14 locales, cuántas veces se quedó sin stock de algún
        ingrediente y cuántas veces subió de forma anómala el precio de un ingrediente, semana a semana (de lunes a
        domingo). Cada local está en su moneda: los de Colombia en pesos (COP) y los de Estados Unidos en dólares (USD),
        sin convertir.
      </p>
      <WeeklyReportPanel />
    </main>
  );
}
