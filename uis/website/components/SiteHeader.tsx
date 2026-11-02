import Image from "next/image";

const NAV_LINKS = [
  { href: "#", label: "Inicio" },
  { href: "#ubicaciones", label: "Ubicaciones" },
  { href: "#menu", label: "Menú" },
  { href: "#brasapoints", label: "Brasa Points" },
  { href: "#contacto", label: "Contacto" },
];

export default function SiteHeader() {
  return (
    <header>
      {/* Barra de navegación responsiva fijada */}
      <nav
        aria-label="Navegación principal"
        className="fixed top-0 left-0 right-0 z-50 w-full border-b border-red-200 bg-white"
      >
        <div className="mx-auto flex h-auto items-center justify-between px-3 md:px-4 lg:max-w-6xl lg:px-8">
          <Image
            src="/media/logo-brasaland.png"
            alt="Logo Brasaland"
            width={1245}
            height={470}
            sizes="191px"
            loading="eager"
            className="h-18 w-auto mt-1.5"
          />

          {/* Menú desktop */}
          <ul className="hidden md:flex md:items-center md:gap-1 lg:gap-3">
            {NAV_LINKS.map((link) => (
              <li key={link.href}>
                <a
                  href={link.href}
                  className="rounded px-3 py-2 text-sm text-red-800 hover:bg-red-100 md:text-sm lg:px-5 lg:text-base"
                >
                  {link.label}
                </a>
              </li>
            ))}
          </ul>

          {/* Menú mobile anclado al ícono: funciona solo con CSS, mediante el checkbox */}
          <div className="relative md:hidden">
            <input
              id="menu-toggle-mobile"
              aria-label="Abrir menú principal"
              type="checkbox"
              className="peer sr-only"
              aria-controls="mobile-menu"
            />

            <label
              htmlFor="menu-toggle-mobile"
              className="block cursor-pointer rounded p-2 hover:bg-red-100"
            >
              <span className="sr-only">Abrir Menú</span>
              <svg
                aria-hidden="true"
                xmlns="http://www.w3.org/2000/svg"
                className="h-6 w-6 text-red-700"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </label>

            <ul
              id="mobile-menu"
              aria-label="Navegación móvil"
              className="hidden absolute right-0 top-full mt-2 z-50 w-max min-w-44 overflow-hidden rounded-md border border-red-200 bg-white shadow-lg peer-checked:block"
            >
              {NAV_LINKS.map((link) => (
                <li key={link.href} className="border-b border-red-100 last:border-b-0">
                  <a
                    href={link.href}
                    className="block whitespace-nowrap px-4 py-3 text-right text-sm text-red-800 hover:bg-red-100"
                  >
                    {link.label}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </nav>
    </header>
  );
}
