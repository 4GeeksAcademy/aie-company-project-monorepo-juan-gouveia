import type { Branch, IncidentCategory, IncidentOrigin, IncidentStatus } from "@/types/incident-manager";

// Textos tomados del briefing "Gestor de Incidencias Centralizado".
// - Sedes: el briefing define un nombre para mostrar; el desplegable lo usa (no el valor interno).
// - Categorías, estados y orígenes: se muestra el código exacto, acompañado solo de la
//   descripción que da el propio briefing.

// Tabla "Sedes de Brasaland", en el mismo orden.
export const BRANCH_LABELS: Record<Branch, string> = {
  central: "Central (Medellín / Miami)",
  medellin_centro: "Medellín Centro",
  medellin_laureles: "Medellín Laureles",
  medellin_envigado: "Medellín Envigado",
  medellin_bello: "Medellín Bello",
  medellin_itagui: "Medellín Itagüí",
  bogota_chapinero: "Bogotá Chapinero",
  bogota_usaquen: "Bogotá Usaquén",
  cali_granada: "Cali Granada",
  barranquilla_norte: "Barranquilla Norte",
  miami_doral: "Miami Doral",
  miami_hialeah: "Miami Hialeah",
  miami_kendall: "Miami Kendall",
  orlando_international: "Orlando International Drive",
  fort_lauderdale: "Fort Lauderdale",
};

// Tabla "Categorías de incidencias".
export const CATEGORY_DESCRIPTIONS: Record<IncidentCategory, string> = {
  equipment_failure: "Fallo de equipamiento de cocina o sala (horno, freidora, cámara frigorífica, TPV)",
  supply_issue: "Problema con insumos: falta de producto, calidad deficiente, entrega incorrecta",
  customer_complaint: "Queja o reclamación de cliente: producto, servicio, tiempo de espera, experiencia",
  staff_issue: "Incidencia relacionada con personal: ausencia, conflicto, accidente laboral leve",
  facility_issue: "Problema de instalaciones: agua, electricidad, climatización, limpieza",
  pos_system: "Error en el sistema de caja o TPV",
  delivery_issue: "Problema con pedidos a domicilio o plataformas de delivery",
  other: "Cualquier incidencia que no encaje en las categorías anteriores",
};

// Tabla "Estados y ciclo de vida".
export const STATUS_DESCRIPTIONS: Record<IncidentStatus, string> = {
  open: "Incidencia recién registrada, pendiente de asignar",
  in_progress: "El equipo de operaciones o el gerente del local está gestionándola",
  resolved: "Incidencia cerrada con solución confirmada",
  discarded: "Registrada por error o duplicada — no requiere acción",
};

// Tabla "Orígenes".
export const ORIGIN_DESCRIPTIONS: Record<IncidentOrigin, string> = {
  customer: "Queja o incidencia comunicada por un cliente (en local, por app, por email)",
  branch: "Reportada por el gerente o personal de un local específico",
  internal: "Detectada por el equipo corporativo (operaciones, tecnología, RRHH)",
};

// Opciones de los desplegables: el texto es el propio código.
function codeOptions<T extends string>(codes: Record<T, string>): Record<T, string> {
  return Object.fromEntries(Object.keys(codes).map((code) => [code, code])) as Record<T, string>;
}

export const CATEGORY_OPTIONS = codeOptions(CATEGORY_DESCRIPTIONS);
export const STATUS_OPTIONS = codeOptions(STATUS_DESCRIPTIONS);
export const ORIGIN_OPTIONS = codeOptions(ORIGIN_DESCRIPTIONS);

// Ciclo de vida del briefing: desde cada estado, a cuáles se puede pasar. resolved y discarded son finales.
// La API lo comprueba igualmente (400 invalid_transition); aquí sirve para ofrecer solo opciones válidas.
export const STATUS_TRANSITIONS: Record<IncidentStatus, IncidentStatus[]> = {
  open: ["in_progress", "discarded"],
  in_progress: ["resolved", "discarded"],
  resolved: [],
  discarded: [],
};
