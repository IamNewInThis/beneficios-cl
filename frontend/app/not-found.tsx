import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center gap-4 px-4 py-24 text-center">
      <h1 className="text-6xl font-bold text-white/20">404</h1>
      <p className="text-sm text-white/50">No encontramos lo que buscabas.</p>
      <Link
        href="/"
        className="rounded-full bg-white px-4 py-1.5 text-sm font-medium text-ink transition hover:bg-white/90"
      >
        Volver al inicio
      </Link>
    </div>
  );
}
