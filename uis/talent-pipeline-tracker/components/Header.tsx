import Image from "next/image";

export default function Header() {
  return (
    <header className="sticky top-0 z-50 border-b border-red-200 bg-white">
      <div className="mx-auto flex items-center gap-2 px-3 py-2 md:px-4 lg:max-w-6xl lg:px-8">
        <Image
          src="/logo-brasaland.png"
          alt="Logo Brasaland"
          width={160}
          height={72}
          className="h-10 w-auto shrink-0 md:h-18"
          priority
        />
        <h1 className="min-w-0 flex-1 truncate text-center text-sm font-semibold text-red-700 md:text-base lg:text-lg">
          Talent Pipeline Tracker
        </h1>
        {/* Espaciador invisible del mismo ancho que el logo, solo en desktop donde sobra espacio para centrar de verdad */}
        <Image
          aria-hidden="true"
          alt=""
          src="/logo-brasaland.png"
          width={160}
          height={72}
          className="hidden h-18 w-auto shrink-0 invisible md:block"
        />
      </div>
    </header>
  );
}
