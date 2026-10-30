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
    href: "/funciones",
    name: "Pruebas de funciones",
    description: "Pruebas manuales de filtros, búsquedas, reportes y validaciones de negocio.",
  },
];
