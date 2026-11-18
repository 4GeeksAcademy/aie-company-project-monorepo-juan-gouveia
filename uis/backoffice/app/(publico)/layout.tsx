import Header from "@/components/Header";

// Vistas sin sesión: login y registro. Sin guard y sin navegación a herramientas.
export default function PublicoLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <Header minimal />
      <main className="px-3 py-10 md:px-4">
        <div className="mx-auto w-full max-w-md rounded-lg border border-red-200 bg-white p-6 shadow-md">
          {children}
        </div>
      </main>
    </>
  );
}
