import { ImageResponse } from "next/og";

// Icono del sitio (convención app/icon de Next.js): una "B" blanca sobre el rojo de la marca
// (red-700 de Tailwind, el de títulos y botones). Se genera en el build como PNG estático y Next.js
// añade el <link rel="icon"> en todas las páginas, así que el navegador ya no pide /favicon.ico,
// que no existía y dejaba un 404 en la consola (P3 de audit/AUDIT.md).
export const size = { width: 32, height: 32 };
export const contentType = "image/png";

export default function Icon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#c10007",
          borderRadius: 6,
          color: "white",
          fontSize: 24,
          fontWeight: 700,
        }}
      >
        B
      </div>
    ),
    { ...size },
  );
}
