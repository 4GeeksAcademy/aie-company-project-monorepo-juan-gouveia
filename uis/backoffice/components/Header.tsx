import Image from "next/image";
import Link from "next/link";
import MobileNav from "@/components/MobileNav";
import NavDropdown, { NAV_ITEM } from "@/components/NavDropdown";
import { toolSections } from "@/lib/tools";

interface HeaderProps {
  // Sin navegación ni cuenta: para el login, el registro y mientras se comprueba la sesión.
  minimal?: boolean;
  // Bloque de cuenta (perfil y cierre de sesión); se muestra también en móvil.
  account?: React.ReactNode;
}

export default function Header({ minimal = false, account }: HeaderProps) {
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
        {/* Desde xl, el menú por secciones en la cabecera. Por debajo no cabe junto a la cuenta, y
            FilterBar depende de la altura fija de esta cabecera, así que no puede pasar a una segunda
            línea: ahí se usa el menú hamburguesa (MobileNav), cuyo panel se superpone a la página. */}
        {!minimal && <MobileNav />}
        {!minimal && (
          <nav aria-label="Herramientas" className="hidden xl:block">
            <ul className="flex items-center justify-end gap-1">
              {toolSections.map((section) => (
                <li key={section.name}>
                  {section.tools.length === 1 ? (
                    // Una sola herramienta: enlace directo con el nombre de la sección.
                    <Link href={section.tools[0].href} className={NAV_ITEM}>
                      {section.name}
                    </Link>
                  ) : (
                    <NavDropdown section={section} />
                  )}
                </li>
              ))}
            </ul>
          </nav>
        )}
        {!minimal && account}
      </div>
    </header>
  );
}
