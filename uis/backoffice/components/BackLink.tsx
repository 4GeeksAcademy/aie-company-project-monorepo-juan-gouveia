import Link from "next/link";

interface BackLinkProps {
  href: string;
  children: React.ReactNode;
}

export default function BackLink({ href, children }: BackLinkProps) {
  return (
    <Link
      href={href}
      className="mb-6 inline-flex items-center gap-1 text-sm font-semibold text-red-700 hover:underline md:text-base"
    >
      ← {children}
    </Link>
  );
}
