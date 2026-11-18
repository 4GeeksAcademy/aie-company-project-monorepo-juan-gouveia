import ProtectedShell from "@/components/auth/ProtectedShell";
import SessionProvider from "@/components/auth/SessionProvider";

// Vistas que requieren sesión: la portada y todas las herramientas (ticket AUTH-02).
// Toda página creada dentro de este grupo queda protegida. El guard corre en el cliente porque el
// token está en localStorage, que el servidor (y proxy.ts) no pueden leer.
export default function ProtegidoLayout({ children }: { children: React.ReactNode }) {
  return (
    <SessionProvider>
      <ProtectedShell>{children}</ProtectedShell>
    </SessionProvider>
  );
}
