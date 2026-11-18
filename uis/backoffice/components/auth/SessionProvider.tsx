"use client";

import { useRouter } from "next/navigation";
import { createContext, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { getCurrentUser } from "@/lib/auth/api";
import { currentPath, LOGIN_PATH, loginUrl } from "@/lib/auth/navigation";
import { clearToken, getToken, subscribeToToken } from "@/lib/auth/token";
import type { CurrentUser } from "@/types/auth";

export type SessionStatus = "checking" | "authenticated" | "error";

export interface SessionValue {
  status: SessionStatus;
  user: CurrentUser | null;
  // Mensaje si /auth/me falla por un motivo que no es la sesión (API caída, 502…).
  error: string | null;
  // Vuelve a pedir /auth/me (tras un error o cuando cambia el perfil).
  refresh: () => void;
  // Sustituye el usuario sin pedirlo a la API (tras guardar el perfil).
  setUser: (user: CurrentUser) => void;
  logout: () => void;
}

export const SessionContext = createContext<SessionValue | null>(null);

// Guard de la zona protegida (ticket AUTH-02, decisiones F-3 y F-8):
// - sin token, redirige a /login?next=<ruta> sin llamar a la API;
// - con token, comprueba la sesión con GET /auth/me. Un 401 o una cuenta desactivada los resuelve
//   el cliente común: borra el token y redirige al login con el motivo;
// - escucha los cambios del token en otras pestañas: si desaparece, redirige; si cambia, recarga el usuario.
export default function SessionProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [status, setStatus] = useState<SessionStatus>("checking");
  const [user, setUserState] = useState<CurrentUser | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Evita que una respuesta antigua de /auth/me pise a una más reciente.
  const requestId = useRef(0);

  // Solo cambia el estado cuando responde la API; el estado inicial ya es "checking".
  const loadUser = useCallback(() => {
    if (!getToken()) {
      router.replace(loginUrl(currentPath()));
      return;
    }

    const id = ++requestId.current;
    getCurrentUser()
      .then((current) => {
        if (id !== requestId.current) return;
        setUserState(current);
        setStatus("authenticated");
      })
      .catch((err: unknown) => {
        if (id !== requestId.current) return;
        // Si fue un 401, el cliente común ya está redirigiendo al login.
        if (!getToken()) return;
        setError(err instanceof Error ? err.message : "No se pudo comprobar la sesión.");
        setStatus("error");
      });
  }, [router]);

  // Para el botón "Reintentar" y los cambios de token de otra pestaña.
  const refresh = useCallback(() => {
    setStatus("checking");
    setError(null);
    loadUser();
  }, [loadUser]);

  useEffect(() => {
    loadUser();
    return subscribeToToken((source) => {
      // En esta pestaña, quien cambia el token ya navega: el login, el cierre de sesión o el cliente común.
      if (source === "this-tab") return;
      if (!getToken()) {
        requestId.current++;
        setUserState(null);
        router.replace(LOGIN_PATH);
      } else {
        refresh();
      }
    });
  }, [loadUser, refresh, router]);

  const logout = useCallback(() => {
    requestId.current++;
    clearToken();
    setUserState(null);
    router.replace(LOGIN_PATH);
  }, [router]);

  const setUser = useCallback((next: CurrentUser) => setUserState(next), []);

  const value = useMemo<SessionValue>(
    () => ({ status, user, error, refresh, setUser, logout }),
    [status, user, error, refresh, setUser, logout]
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}
