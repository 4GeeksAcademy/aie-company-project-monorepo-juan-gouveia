export interface Tool {
  href: string;
  name: string;
  description: string;
}

// La portada y la navegación se generan desde este registro: cada herramienta nueva
// necesita su carpeta en app/ y una entrada aquí.
export const tools: Tool[] = [
  {
    href: "/talento",
    name: "Talent Pipeline Tracker",
    description: "Seguimiento de candidatos del proceso de selección de Brasaland.",
  },
  {
    href: "/incidencias",
    name: "Análisis de incidencias",
    description: "Valida el CSV de incidentes de Operaciones, resume sus métricas y exporta los resultados.",
  },
  {
    href: "/gestor-incidencias",
    name: "Gestor de incidencias",
    description: "Resumen por estado, categoría, origen y sede, y listado con filtros para hacer seguimiento y cambiar estados.",
  },
  {
    href: "/gestor-incidencias/nueva",
    name: "Registrar incidencia",
    description: "Registra una incidencia operativa, de cliente o interna en cualquier sede, con su categoría y su origen.",
  },
  {
    href: "/proveedores",
    name: "Directorio de proveedores",
    description: "Proveedores activos y suspendidos de Colombia y USA, con sus categorías y tarifas vigentes.",
  },
  {
    href: "/funciones",
    name: "Pruebas de funciones",
    description: "Pruebas manuales de filtros, búsquedas, reportes y validaciones de negocio.",
  },
];
