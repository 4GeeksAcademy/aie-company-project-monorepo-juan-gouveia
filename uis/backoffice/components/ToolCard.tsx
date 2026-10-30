import Link from "next/link";
import type { Tool } from "@/lib/tools";

export default function ToolCard({ tool }: { tool: Tool }) {
  return (
    <Link
      href={tool.href}
      className="rounded-lg bg-white p-4 shadow-md transition hover:shadow-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700 focus-visible:ring-offset-2"
    >
      <h2 className="mb-2 text-md font-semibold text-red-700 md:text-lg">{tool.name}</h2>
      <p className="text-sm text-black md:text-base">{tool.description}</p>
    </Link>
  );
}
