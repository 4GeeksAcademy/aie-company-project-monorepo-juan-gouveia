import { formatDateTime } from "@/lib/format";
import { freshnessOf, isCurrentWeek, STALE_AFTER_DAYS } from "@/lib/weekly-report";
import type { PipelineRun } from "@/types/weekly-report";

interface ReportNoticesProps {
  weekStart: string;
  latestRun: PipelineRun | null | undefined;
  // Ningún local tuvo actividad en la semana mostrada.
  silentWeek: boolean;
  now: Date;
}

function Notice({ tone, children }: { tone: "info" | "warning"; children: React.ReactNode }) {
  const style =
    tone === "warning" ? "border-amber-300 bg-amber-50 text-black" : "border-red-200 bg-white text-black";
  return <p className={`rounded-lg border p-3 text-sm shadow-md ${style}`}>{children}</p>;
}

// Cuándo se actualizaron los datos y los avisos que cambian cómo leerlos: datos desactualizados, una
// actualización fallida, la semana en curso (parcial) o una semana sin ninguna actividad.
export default function ReportNotices({ weekStart, latestRun, silentWeek, now }: ReportNoticesProps) {
  const freshness = freshnessOf(latestRun, now);

  return (
    <div className="flex flex-col gap-2" aria-live="polite">
      {freshness.status === "fresh" && (
        <Notice tone="info">
          Datos actualizados el <time dateTime={freshness.at}>{formatDateTime(freshness.at)}</time>. El reporte se
          actualiza cada lunes a las 6:00 (hora de Bogotá).
        </Notice>
      )}
      {freshness.status === "updating" && (
        <Notice tone="info">Los datos se están actualizando en este momento. Vuelve a cargar en unos minutos.</Notice>
      )}
      {freshness.status === "stale" && (
        <Notice tone="warning">
          El reporte no se actualiza desde el <time dateTime={freshness.at}>{formatDateTime(freshness.at)}</time> (más
          de {STALE_AFTER_DAYS} días): las semanas recientes pueden faltar. Avisa al equipo de tecnología.
        </Notice>
      )}
      {freshness.status === "failed" && (
        <Notice tone="warning">
          La última actualización, el <time dateTime={freshness.at}>{formatDateTime(freshness.at)}</time>, no se
          completó: los datos pueden no estar al día. Avisa al equipo de tecnología.
        </Notice>
      )}
      {isCurrentWeek(weekStart, now) && (
        <Notice tone="warning">Semana en curso: los datos son parciales hasta que termine el domingo.</Notice>
      )}
      {silentWeek && (
        <Notice tone="warning">
          Ningún local registró compras, mermas, quiebres de stock ni alertas de precio esta semana. Si debería
          haberlos, puede ser un fallo en la captura de datos: avisa al equipo de tecnología.
        </Notice>
      )}
    </div>
  );
}
