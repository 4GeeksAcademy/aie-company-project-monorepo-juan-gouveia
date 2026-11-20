import { toolSections, tools } from "@/lib/tools";

describe("toolSections", () => {
  it("sigue el orden del menú: Inventario, Proveedores, Incidencias y Herramientas", () => {
    expect(toolSections.map((section) => section.name)).toEqual([
      "Inventario",
      "Proveedores",
      "Incidencias",
      "Herramientas",
    ]);
  });

  it("agrupa las tres herramientas de incidencias y las tres internas", () => {
    const byName = Object.fromEntries(toolSections.map((section) => [section.name, section.tools.map((tool) => tool.href)]));
    expect(byName.Incidencias).toEqual(["/incidencias", "/gestor-incidencias", "/gestor-incidencias/nueva"]);
    expect(byName.Herramientas).toEqual(["/talento", "/funciones", "/telemetria"]);
  });

  it("no tiene secciones vacías", () => {
    for (const section of toolSections) expect(section.tools.length).toBeGreaterThan(0);
  });
});

describe("tools", () => {
  it("reúne las 8 herramientas, sin rutas repetidas", () => {
    expect(tools).toHaveLength(8);
    expect(new Set(tools.map((tool) => tool.href)).size).toBe(8);
  });
});
