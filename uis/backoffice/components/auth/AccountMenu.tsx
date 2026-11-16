"use client";

import Link from "next/link";
import Tooltip from "@/components/Tooltip";
import { useSession } from "@/hooks/useSession";

const ITEM =
  "flex h-10 items-center gap-2 rounded px-2 text-sm text-red-800 hover:bg-red-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700";

function UserIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-5 w-5 shrink-0">
      <circle cx="12" cy="8" r="4" />
      <path d="M4 20c0-4 4-6 8-6s8 2 8 6" strokeLinecap="round" />
    </svg>
  );
}

function LogoutIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-5 w-5 shrink-0">
      <path d="M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3" strokeLinecap="round" />
      <path d="M10 8l-4 4 4 4M6 12h10" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

// Bloque de cuenta de la cabecera: solo iconos en todos los tamaños, con aria-label para los lectores
// de pantalla y un Tooltip propio al pasar el ratón o llegar con el teclado. Así deja sitio al menú y
// no cambia la altura fija de la cabecera de la que depende FilterBar.
export default function AccountMenu() {
  const { user, logout } = useSession();
  if (!user) return null;

  const displayName = user.profile?.name || user.email;

  return (
    <div className="flex shrink-0 items-center gap-1 border-l border-red-100 pl-2">
      <Tooltip label={displayName}>
        <Link href="/account/profile" className={ITEM} aria-label={`Mi perfil (${displayName})`}>
          <UserIcon />
        </Link>
      </Tooltip>
      <Tooltip label="Cerrar sesión">
        <button type="button" onClick={logout} className={ITEM} aria-label="Cerrar sesión">
          <LogoutIcon />
        </button>
      </Tooltip>
    </div>
  );
}
