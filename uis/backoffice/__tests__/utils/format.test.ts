// Formateadores de fechas y métricas (lib/format.ts). jest.config.js fija TZ=UTC, así que las fechas
// "locales" de estas pruebas son UTC en cualquier equipo.
import { formatDate, formatDateTime, formatDateTimeUtc, formatDecimal, formatPercentage } from "@/lib/format";

const MISSING = "—";
// Valores que llegan de las APIs cuando falta la fecha o viene corrupta.
const BAD_DATES = [null, undefined, "", "no-es-una-fecha", "2026-13-45"];

describe("formatDate", () => {
  it("muestra el día, el mes en palabras y el año", () => {
    expect(formatDate("2026-09-18T14:30:00Z")).toBe("18 de septiembre de 2026");
  });

  it.each(BAD_DATES)("muestra — y nunca 'Invalid Date' ni 1970 con %p", (value) => {
    expect(formatDate(value)).toBe(MISSING);
  });
});

describe("formatDateTime", () => {
  it("muestra la fecha abreviada y la hora", () => {
    expect(formatDateTime("2026-09-18T14:30:00Z")).toBe("18 sept 2026, 14:30");
  });

  it.each(BAD_DATES)("muestra — con %p", (value) => {
    expect(formatDateTime(value)).toBe(MISSING);
  });
});

describe("formatDateTimeUtc", () => {
  it("muestra la hora en UTC con la zona explícita", () => {
    expect(formatDateTimeUtc("2024-01-14T00:00:00Z")).toBe("14 ene 2024, 0:00 UTC");
  });

  it("no depende de la zona del equipo: medianoche UTC sigue siendo el mismo día", () => {
    // Una fecha con desfase (-05:00, Colombia) se convierte a UTC antes de mostrarse.
    expect(formatDateTimeUtc("2024-01-13T19:00:00-05:00")).toBe("14 ene 2024, 0:00 UTC");
  });

  it.each(BAD_DATES)("muestra — con %p", (value) => {
    expect(formatDateTimeUtc(value)).toBe(MISSING);
  });
});

describe("formatPercentage", () => {
  it("usa un decimal con punto, como el reporte de Operaciones", () => {
    expect(formatPercentage(30.208)).toBe("30.2%");
    expect(formatPercentage(0)).toBe("0.0%");
  });

  it("muestra — cuando no hay porcentaje (total en 0)", () => {
    expect(formatPercentage(null)).toBe(MISSING);
  });
});

describe("formatDecimal", () => {
  it("redondea a dos decimales por defecto o a los indicados", () => {
    expect(formatDecimal(3.456)).toBe("3.46");
    expect(formatDecimal(4, 1)).toBe("4.0");
  });

  it("no oculta un valor no numérico: NaN se muestra tal cual", () => {
    // Documenta el comportamiento actual: quien llama debe pasar un número válido.
    expect(formatDecimal(Number.NaN)).toBe("NaN");
  });
});
