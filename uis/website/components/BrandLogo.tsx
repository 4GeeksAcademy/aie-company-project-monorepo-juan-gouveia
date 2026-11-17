import Image from "next/image";

// Logo de Brasaland de las cabeceras. Concentra en un solo sitio la configuración de carga:
// - `sizes="191px"`: el CSS lo muestra a 72 px de alto (h-18) y el original es 1245×470, así que
//   ocupa ~191 px de ancho. Con eso Next.js sirve una versión de 256–384 px (unos 5 KB) en lugar del PNG
//   original (43 KB).
// - `loading="eager"`: está en la cabecera fija, visible desde el primer pintado en todas las páginas.
// - `width`/`height` reservan su espacio, así que no provoca desplazamientos (CLS).
export default function BrandLogo() {
  return (
    <Image
      src="/media/logo-brasaland.png"
      alt="Logo Brasaland"
      width={1245}
      height={470}
      sizes="191px"
      loading="eager"
      className="h-18 w-auto mt-1.5"
    />
  );
}
