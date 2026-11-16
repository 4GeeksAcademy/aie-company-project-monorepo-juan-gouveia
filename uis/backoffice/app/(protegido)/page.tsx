import ToolCard from "@/components/ToolCard";
import { toolSections } from "@/lib/tools";

// Portada: las mismas secciones que el menú de la cabecera, en el mismo orden.
export default function Home() {
  return (
    <main className="px-3 py-6 md:px-4 lg:mx-auto lg:max-w-6xl lg:px-8">
      <h1 className="mb-6 text-xl font-semibold text-red-700 md:text-2xl lg:text-3xl">
        Herramientas internas
      </h1>

      <div className="flex flex-col gap-8">
        {toolSections.map((section) => {
          const headingId = `seccion-${section.name.toLowerCase()}`;
          return (
            <section key={section.name} aria-labelledby={headingId}>
              <h2 id={headingId} className="mb-3 text-lg font-semibold text-red-800 md:text-xl">
                {section.name}
              </h2>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                {section.tools.map((tool) => (
                  <ToolCard key={tool.href} tool={tool} />
                ))}
              </div>
            </section>
          );
        })}
      </div>
    </main>
  );
}
