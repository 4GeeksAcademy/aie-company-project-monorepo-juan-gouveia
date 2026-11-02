export default function DetailItem({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <dt className="text-sm font-semibold text-red-700">{label}</dt>
      <dd className="text-black">{children}</dd>
    </div>
  );
}
