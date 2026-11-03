// Textos tomados del briefing de Operaciones (docs/_private/briefing-csv-reader.md).
// La interfaz muestra siempre el código exacto que envía la API (CUSTOMER_COMPLAINT, OPEN…);
// estos textos solo lo acompañan. Si llega un código desconocido, se muestra sin descripción.

// Tabla "Categorías válidas" del briefing.
const CATEGORY_DESCRIPTIONS: Record<string, string> = {
  CUSTOMER_COMPLAINT: "Queja de cliente (servicio, tiempo de espera, trato)",
  EQUIPMENT: "Falla o avería de equipamiento",
  SUPPLY: "Problema de abastecimiento o falta de stock",
  FOOD_QUALITY: "Incidente de calidad de alimentos",
  STAFF: "Incidente relacionado con personal",
};

// Tabla "Reglas de registros inválidos" del briefing. invalid_status no está en el briefing:
// la añade la API para que un estado desconocido no cuente como válido.
const RULE_LABELS: Record<string, string> = {
  missing_location: "Falta location_id",
  invalid_category: "category faltante o inválida",
  empty_description: "description vacía o demasiado corta",
  missing_reporter: "Falta reporter_id",
  invalid_status: "status faltante o inválido",
  closed_without_score: "status = CLOSED sin satisfaction_score",
  score_out_of_range: "satisfaction_score fuera de rango",
};

export function categoryDescription(code: string): string | undefined {
  return CATEGORY_DESCRIPTIONS[code];
}

export function ruleLabel(rule: string, fallback?: string): string {
  return RULE_LABELS[rule] ?? fallback ?? rule;
}
