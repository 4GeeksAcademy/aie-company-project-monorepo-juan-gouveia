import Image from "next/image";
import Link from "next/link";

export default function RegistrationHeader() {
  return (
    <header>
      <nav
        aria-label="Navegación principal"
        className="fixed top-0 left-0 right-0 z-50 w-full border-b border-red-200 bg-white"
      >
        <div className="mx-auto flex h-auto items-center justify-between px-3 md:px-4 lg:max-w-6xl lg:px-8">
          <Link href="/" aria-label="Volver a la página principal">
            <Image
              src="/media/logo-brasaland.png"
              alt="Logo Brasaland"
              width={1245}
              height={470}
              sizes="191px"
              loading="eager"
              className="h-18 w-auto mt-1.5"
            />
          </Link>
        </div>
      </nav>
    </header>
  );
}
