import Link from "next/link";

export function Nav() {
  return (
    <nav className="border-b border-hairline-dark bg-black">
      <div className="mx-auto flex h-12 max-w-7xl items-center justify-between px-4">
        <Link href="/" className="text-sm font-semibold tracking-tight text-white hover:text-white/80 transition">
          Beneficios CL
        </Link>
        <div className="flex items-center gap-4 text-sm text-white/50">
          <Link href="/" className="hover:text-white transition">
            Inicio
          </Link>
          <Link href="/about" className="hover:text-white transition">
            Acerca de
          </Link>
        </div>
      </div>
    </nav>
  );
}
