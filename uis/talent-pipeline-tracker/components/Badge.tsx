export default function Badge({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded border border-red-200 px-2 py-1 text-red-700">{children}</span>
  );
}
