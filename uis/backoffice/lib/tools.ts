export interface Tool {
  href: string;
  name: string;
  description: string;
}

// Sección del menú y de la portada. Con una sola herramienta, la cabecera muestra un enlace directo
// con el nombre de la sección; con varias, un desplegable.
export interface ToolSection {
  name: string;
  tools: Tool[];
}

// La portada y la navegación se generan desde este registro, en este orden (de izquierda a derecha
// en la cabecera, de arriba abajo en la portada). Cada herramienta nueva necesita su carpeta en app/
// y una entrada aquí, dentro de su sección.
export const toolSections: ToolSection[] = [
  {
    name: "Reportes",
    tools: [
      {
        href: "/reporte-semanal",
        name: "Reporte semanal de costo y merma",
        description:
          "Costo de compra, costo de merma, ratio de merma, quiebres de stock y alertas de precio de cada local, semana a semana. Para administradores y gerentes.",
      },
    ],
  },
  {
    name: "Inventario",
    tools: [
      {
        href: "/inventario/ingredientes",
        name: "Inventario",
        description: "Stock actual de cada ingrediente, registro de entradas y salidas, e historial de órdenes.",
      },
    ],
  },
  {
    name: "Proveedores",
    tools: [
      {
        href: "/proveedores",
        name: "Directorio de proveedores",
        description: "Proveedores activos y suspendidos de Colombia y USA, con sus categorías y tarifas vigentes.",
      },
    ],
  },
  {
    name: "Incidencias",
    tools: [
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
    ],
  },
  {
    name: "Herramientas",
    tools: [
      {
        href: "/talento",
        name: "Talent Pipeline Tracker",
        description: "Seguimiento de candidatos del proceso de selección de Brasaland.",
      },
      {
        href: "/funciones",
        name: "Pruebas de funciones",
        description: "Pruebas manuales de filtros, búsquedas, reportes y validaciones de negocio.",
      },
      {
        href: "/telemetria",
        name: "Telemetría técnica",
        description: "Volumen de eventos, fallos, latencia de la API y fallos de login por día. Solo administradores.",
      },
    ],
  },
];

// Todas las herramientas en una lista, en el mismo orden.
export const tools: Tool[] = toolSections.flatMap((section) => section.tools);
