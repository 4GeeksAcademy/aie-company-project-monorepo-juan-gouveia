import Link from "next/link";

export default function BrasaPointsCta() {
  return (
    <div className="mt-6 flex justify-end">
      <Link
        href="/registro"
        className="inline-flex items-center justify-center rounded-md bg-red-700 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-red-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700 focus-visible:ring-offset-2 md:text-base"
      >
        Únete a Brasa Points
      </Link>
    </div>
  );
}
