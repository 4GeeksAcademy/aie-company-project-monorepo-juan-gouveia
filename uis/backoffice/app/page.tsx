import ToolCard from "@/components/ToolCard";
import { tools } from "@/lib/tools";

export default function Home() {
  return (
    <main className="px-3 py-6 md:px-4 lg:mx-auto lg:max-w-6xl lg:px-8">
      <h1 className="mb-6 text-xl font-semibold text-red-700 md:text-2xl lg:text-3xl">
        Herramientas internas
      </h1>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {tools.map((tool) => (
          <ToolCard key={tool.href} tool={tool} />
        ))}
      </div>
    </main>
  );
}
