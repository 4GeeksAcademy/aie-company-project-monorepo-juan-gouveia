"use client";

import { useContext } from "react";
import { SessionContext, type SessionValue } from "@/components/auth/SessionProvider";

// Sesión de la zona protegida. Solo funciona dentro de SessionProvider (app/(protegido)/layout.tsx).
export function useSession(): SessionValue {
  const session = useContext(SessionContext);
  if (!session) throw new Error("useSession debe usarse dentro de SessionProvider.");
  return session;
}
