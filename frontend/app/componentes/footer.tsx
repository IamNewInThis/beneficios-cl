export function Footer() {
  return (
    <footer className="border-t border-hairline-dark bg-black">
      <div className="mx-auto flex max-w-7xl flex-col items-center gap-2 px-4 py-6 text-xs text-white/30 sm:flex-row sm:justify-between">
        <p>
          Hecho en Chile 🇨🇱 — Los datos provienen de sitios públicos de cada banco.
        </p>
        <a
          href="https://github.com/anomalyco/beneficios-cl"
          target="_blank"
          rel="noopener noreferrer"
          className="hover:text-white/60 transition underline"
        >
          GitHub
        </a>
      </div>
    </footer>
  );
}
