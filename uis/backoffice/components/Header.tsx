import Image from "next/image";
import Link from "next/link";
import { tools } from "@/lib/tools";

export default function Header() {
  return (
    <header className="sticky top-0 z-50 border-b border-red-200 bg-white">
      <div className="mx-auto flex items-center gap-2 px-3 py-2 md:px-4 lg:max-w-6xl lg:px-8">
        <Link
          href="/"
          aria-label="Ir a la portada del backoffice"
          className="shrink-0 rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700 focus-visible:ring-offset-2"
        >
          <Image
            src="/logo-brasaland.png"
            alt="Logo Brasaland"
            width={1245}
            height={470}
            sizes="(min-width: 768px) 191px, 106px"
            className="h-10 w-auto md:h-18"
            loading="eager"
          />
        </Link>
        <p className="min-w-0 flex-1 truncate text-sm font-semibold text-red-700 md:text-base lg:text-lg">
          Backoffice
        </p>
        {/* En móvil se navega desde la portada: FilterBar depende de la altura fija de esta cabecera. */}
        <nav aria-label="Herramientas" className="hidden md:block">
          <ul className="flex justify-end gap-1">
            {tools.map((tool) => (
              <li key={tool.href}>
                <Link
                  href={tool.href}
                  className="block rounded px-3 py-2 text-sm text-red-800 hover:bg-red-100"
                >
                  {tool.name}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      </div>
    </header>
  );
}
