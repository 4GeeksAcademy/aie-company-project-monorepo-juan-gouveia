import type { Metadata } from "next";
import TelemetryReportPanel from "@/components/telemetria/TelemetryReportPanel";

export const metadata: Metadata = {
  title: "Telemetría técnica",
  description: "Reporte técnico de la telemetría: volumen, fallos, latencia de la API y fallos de login por día.",
};

export default function TelemetryReportPage() {
  return (
    <>
      <h1 className="mb-2 text-xl font-semibold text-red-700 md:text-2xl lg:text-3xl">Telemetría técnica</h1>
      <p className="mb-6 text-sm text-black md:text-base">
        Estado del sistema según los eventos de telemetría guardados: volumen, avisos y errores, latencia de la API y
        fallos de inicio de sesión, por día. Es una vista para el equipo de ingeniería, solo para administradores. El
        reporte se recalcula como mucho una vez por minuto.
      </p>
      <TelemetryReportPanel />
    </>
  );
}
