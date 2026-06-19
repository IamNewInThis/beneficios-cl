"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  agruparPorComercio,
  type BeneficioDetalle,
  type ComercioConBeneficios,
} from "@/lib/types";

const DIAS = [
  "domingo", "lunes", "martes", "miercoles",
  "jueves", "viernes", "sabado",
];

function diaDeHoy(): string {
  return DIAS[new Date().getDay()];
}

function diasSemana(): string[] {
  const hoy = new Date().getDay();
  return Array.from({ length: 7 }, (_, i) => DIAS[(hoy + i) % 7]);
}

// Un beneficio sigue vigente si no tiene fecha de término (no sabemos cuándo
// vence → lo mostramos) o si la fecha es hoy o futura. Solo escondemos los que
// tienen una `vigencia_hasta` explícita ya pasada.
function estaVigente(b: BeneficioDetalle): boolean {
  if (!b.vigencia_hasta) return true;
  const hoy = new Date().toISOString().slice(0, 10); // YYYY-MM-DD
  return b.vigencia_hasta.slice(0, 10) >= hoy;
}

function filtrarPorVentana(
  items: BeneficioDetalle[],
  ventana: "hoy" | "semana"
): BeneficioDetalle[] {
  const permitidos = ventana === "hoy" ? [diaDeHoy()] : diasSemana();
  return items.filter(
    (b) => estaVigente(b) && (
      !b.dias || b.dias.length === 0 ||
      b.dias.some((d) => permitidos.includes(d.toLowerCase()))
    )
  );
}

function shuffle<T>(arr: T[]): T[] {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function fechaFormateada(): string {
  const d = new Date();
  const dias = ["domingo", "lunes", "martes", "miércoles", "jueves", "viernes", "sábado"];
  const meses = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
  return `${dias[d.getDay()]} ${d.getDate()} ${meses[d.getMonth()]}`;
}

function haceTiempo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `hace ${mins} min`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `hace ${hrs} h`;
  return `hace ${Math.floor(hrs / 24)} d`;
}

function maxActualizacion(items: BeneficioDetalle[]): string | null {
  if (items.length === 0) return null;
  return items.reduce((a, b) => (a.actualizado_en > b.actualizado_en ? a : b)).actualizado_en;
}

function formatoValor(b: BeneficioDetalle): string {
  if (b.tipo === "porcentaje") return `${b.valor}%`;
  return `$${b.valor.toLocaleString("es-CL")}`;
}

function resumirDias(dias: string[]): string {
  if (!dias || dias.length === 0) return "Todos los días";
  const mapa: Record<string, string> = {
    lunes: "Lun", martes: "Mar", miercoles: "Mié",
    jueves: "Jue", viernes: "Vie", sabado: "Sáb", domingo: "Dom",
  };
  return dias.map((d) => mapa[d.toLowerCase()] || d).join(", ");
}

export function BeneficiosApp({ beneficios }: { beneficios: BeneficioDetalle[] }) {
  const [ventana, setVentana] = useState<"hoy" | "semana">("hoy");
  const [busqueda, setBusqueda] = useState("");
  const [filtroCategoria, setFiltroCategoria] = useState<string | null>(null);
  const [filtroTarjeta, setFiltroTarjeta] = useState<string | null>(null);
  const [seleccionado, setSeleccionado] = useState<ComercioConBeneficios | null>(null);
  const [shuffled, setShuffled] = useState(false);
  const mountedRef = useRef(false);

  const categorias = useMemo(() => {
    const set = new Set(beneficios.map((b) => b.categoria));
    return ["todas", ...set].sort();
  }, [beneficios]);

  const tarjetas = useMemo(() => {
    const set = new Set(beneficios.map((b) => b.tarjeta));
    return ["todas", ...set].sort();
  }, [beneficios]);

  useEffect(() => {
    mountedRef.current = true;
    setShuffled(true);
  }, []);

  const comercios = useMemo(() => {
    let filtrados = filtrarPorVentana(beneficios, ventana);

    if (busqueda) {
      const q = busqueda.toLowerCase();
      filtrados = filtrados.filter(
        (b) =>
          b.comercio.toLowerCase().includes(q) ||
          b.tarjeta.toLowerCase().includes(q)
      );
    }
    if (filtroCategoria) {
      filtrados = filtrados.filter((b) => b.categoria === filtroCategoria);
    }
    if (filtroTarjeta) {
      filtrados = filtrados.filter((b) => b.tarjeta === filtroTarjeta);
    }

    const grupos = agruparPorComercio(filtrados);
    return shuffled ? shuffle(grupos) : grupos;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [beneficios, ventana, busqueda, filtroCategoria, filtroTarjeta, shuffled]);

  const ultimaActualizacion = maxActualizacion(beneficios);

  return (
    <div className="mx-auto max-w-7xl px-4 py-4">
      <Header
        ventana={ventana}
        onChangeVentana={setVentana}
        busqueda={busqueda}
        onChangeBusqueda={setBusqueda}
        fecha={fechaFormateada()}
        ultimaActualizacion={ultimaActualizacion}
      />

      <MobileFilters
        categorias={categorias}
        tarjetas={tarjetas}
        filtroCategoria={filtroCategoria}
        filtroTarjeta={filtroTarjeta}
        onChangeCategoria={setFiltroCategoria}
        onChangeTarjeta={setFiltroTarjeta}
      />

      <div className="lg:flex lg:gap-6">
        <SidebarFilters
          categorias={categorias}
          tarjetas={tarjetas}
          filtroCategoria={filtroCategoria}
          filtroTarjeta={filtroTarjeta}
          onChangeCategoria={setFiltroCategoria}
          onChangeTarjeta={setFiltroTarjeta}
        />

        <div className="flex-1">
          {comercios.length > 0 && (
            <p className="mt-4 text-xs text-white/30">
              {comercios.length} {comercios.length === 1 ? "comercio" : "comercios"} ·{" "}
              {comercios.reduce((s, c) => s + c.beneficios.length, 0)} beneficios
            </p>
          )}
          {comercios.length === 0 ? (
            <div className="mt-12 rounded-card border border-hairline-dark p-8 text-center text-white/40">
              {beneficios.length === 0
                ? "No hay beneficios cargados todavía. Configura Supabase y corre el scraper para poblar la base de datos."
                : "Ningún beneficio coincide con los filtros actuales."}
            </div>
          ) : (
            <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {comercios.map((c) => (
                <Card
                  key={c.comercio}
                  comercio={c}
                  onClick={() => setSeleccionado(c)}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {seleccionado && (
        <ModalDetalle
          comercio={seleccionado}
          onClose={() => setSeleccionado(null)}
        />
      )}
    </div>
  );
}

function Header({
  ventana,
  onChangeVentana,
  busqueda,
  onChangeBusqueda,
  fecha,
  ultimaActualizacion,
}: {
  ventana: "hoy" | "semana";
  onChangeVentana: (v: "hoy" | "semana") => void;
  busqueda: string;
  onChangeBusqueda: (v: string) => void;
  fecha: string;
  ultimaActualizacion: string | null;
}) {
  return (
    <header>
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold tracking-tight">Beneficios</h1>
        <div className="flex items-center gap-3">
          <div className="relative">
            <input
              type="search"
              placeholder="Buscar..."
              value={busqueda}
              onChange={(e) => onChangeBusqueda(e.target.value)}
              className="w-40 rounded-full bg-surface-elevated py-1.5 pl-8 pr-3 text-sm text-white placeholder-white/40 outline-none border border-transparent focus:border-white/20 transition"
            />
            <svg className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-white/40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
          <button className="text-white/40 hover:text-white transition" title="Ajustes (próximamente)">
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </button>
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-3">
        <div className="flex rounded-full bg-surface-elevated p-0.5">
          <button
            onClick={() => onChangeVentana("hoy")}
            className={`rounded-full px-4 py-1 text-sm font-medium transition ${
              ventana === "hoy"
                ? "bg-white text-ink"
                : "text-white/60 hover:text-white"
            }`}
          >
            Hoy
          </button>
          <button
            onClick={() => onChangeVentana("semana")}
            className={`rounded-full px-4 py-1 text-sm font-medium transition ${
              ventana === "semana"
                ? "bg-white text-ink"
                : "text-white/60 hover:text-white"
            }`}
          >
            Semana
          </button>
        </div>
        <span className="text-sm text-white/40">📅 {fecha}</span>
        {ultimaActualizacion && (
          <span className="ml-auto text-xs text-white/40">
            Actualizado {haceTiempo(ultimaActualizacion)}
          </span>
        )}
      </div>
    </header>
  );
}

function MobileFilters({
  categorias,
  tarjetas,
  filtroCategoria,
  filtroTarjeta,
  onChangeCategoria,
  onChangeTarjeta,
}: {
  categorias: string[];
  tarjetas: string[];
  filtroCategoria: string | null;
  filtroTarjeta: string | null;
  onChangeCategoria: (v: string | null) => void;
  onChangeTarjeta: (v: string | null) => void;
}) {
  return (
    <div className="mt-3 flex gap-2 overflow-x-auto pb-2 lg:hidden">
      <select
        value={filtroCategoria ?? "todas"}
        onChange={(e) => onChangeCategoria(e.target.value === "todas" ? null : e.target.value)}
        className="shrink-0 rounded-full bg-surface-elevated px-3 py-1.5 text-sm text-white border border-hairline-dark outline-none"
      >
        {categorias.map((cat) => (
          <option key={cat} value={cat}>
            {cat === "todas" ? "Categoría" : cat}
          </option>
        ))}
      </select>
      <select
        value={filtroTarjeta ?? "todas"}
        onChange={(e) => onChangeTarjeta(e.target.value === "todas" ? null : e.target.value)}
        className="shrink-0 rounded-full bg-surface-elevated px-3 py-1.5 text-sm text-white border border-hairline-dark outline-none"
      >
        {tarjetas.map((t) => (
          <option key={t} value={t}>
            {t === "todas" ? "Tarjeta" : t}
          </option>
        ))}
      </select>
    </div>
  );
}

function SidebarFilters({
  categorias,
  tarjetas,
  filtroCategoria,
  filtroTarjeta,
  onChangeCategoria,
  onChangeTarjeta,
}: {
  categorias: string[];
  tarjetas: string[];
  filtroCategoria: string | null;
  filtroTarjeta: string | null;
  onChangeCategoria: (v: string | null) => void;
  onChangeTarjeta: (v: string | null) => void;
}) {
  return (
    <aside className="hidden w-56 shrink-0 lg:block">
      <div className="mt-4 space-y-6">
        <div>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-white/40">
            Categoría
          </h3>
          <div className="space-y-1">
            {categorias.map((cat) => (
              <button
                key={cat}
                onClick={() => onChangeCategoria(cat === "todas" ? null : cat)}
                className={`block w-full rounded-full px-3 py-1.5 text-left text-sm transition ${
                  (cat === "todas" && !filtroCategoria) || filtroCategoria === cat
                    ? "bg-white text-ink font-medium"
                    : "text-white/60 hover:text-white"
                }`}
              >
                {cat === "todas" ? "Todas" : cat}
              </button>
            ))}
          </div>
        </div>
        <div>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-white/40">
            Tarjeta
          </h3>
          <div className="space-y-1">
            {tarjetas.map((t) => (
              <button
                key={t}
                onClick={() => onChangeTarjeta(t === "todas" ? null : t)}
                className={`block w-full rounded-full px-3 py-1.5 text-left text-sm transition ${
                  (t === "todas" && !filtroTarjeta) || filtroTarjeta === t
                    ? "bg-white text-ink font-medium"
                    : "text-white/60 hover:text-white"
                }`}
              >
                {t === "todas" ? "Todas" : t}
              </button>
            ))}
          </div>
        </div>
      </div>
    </aside>
  );
}

function Card({
  comercio,
  onClick,
}: {
  comercio: ComercioConBeneficios;
  onClick: () => void;
}) {
  const diasUnicos = [
    ...new Set(
      comercio.beneficios.flatMap((b) =>
        b.dias && b.dias.length > 0 ? b.dias.map((d) => d.toLowerCase()) : []
      )
    ),
  ];

  const MAX_VISIBLE = 3;
  const visibles = comercio.beneficios.slice(0, MAX_VISIBLE);
  const ocultos = comercio.beneficios.length - visibles.length;

  return (
    <article
      onClick={onClick}
      className="flex cursor-pointer flex-col rounded-card border border-hairline-light bg-white p-4 transition hover:border-gray-300"
    >
      <div className="mb-2 flex items-start justify-between gap-2">
        <h2 className="truncate text-base font-semibold text-ink">{comercio.comercio}</h2>
        <span className="shrink-0 rounded-full bg-surface-soft px-2 py-0.5 text-xs font-medium text-ink">
          {comercio.categoria}
        </span>
      </div>
      <ul className="space-y-1.5 text-sm">
        {visibles.map((b) => (
          <li key={b.id} className="flex justify-between gap-2">
            <span className="truncate text-mute">
              {b.tarjeta}{" "}
              <span className="text-stone">({b.medio_pago})</span>
            </span>
            <span className="shrink-0 font-semibold text-ink">
              {formatoValor(b)}
            </span>
          </li>
        ))}
      </ul>
      {ocultos > 0 && (
        <p className="mt-1.5 text-xs font-medium text-stone">
          +{ocultos} {ocultos === 1 ? "tarjeta" : "tarjetas"} más
        </p>
      )}
      {diasUnicos.length > 0 && (
        <p className="mt-2 truncate text-xs text-stone">
          {resumirDias(diasUnicos)}
        </p>
      )}
    </article>
  );
}

function ModalDetalle({
  comercio,
  onClose,
}: {
  comercio: ComercioConBeneficios;
  onClose: () => void;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/60 lg:items-center"
      onClick={onClose}
    >
      <div
        className="max-h-[85vh] w-full overflow-y-auto rounded-t-card bg-surface-elevated p-6 lg:max-w-lg lg:rounded-card"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <button onClick={onClose} className="text-white/60 hover:text-white transition">
              <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            <h2 className="text-lg font-semibold text-white">{comercio.comercio}</h2>
          </div>
          <span className="rounded-full bg-white/10 px-2 py-0.5 text-xs font-medium text-white">
            {comercio.categoria}
          </span>
        </div>

        <div className="divide-y divide-hairline-dark">
          {comercio.beneficios.map((b) => (
            <div key={b.id} className="flex items-center justify-between py-3">
              <div>
                <p className="text-sm font-medium text-white">
                  {b.tarjeta}{" "}
                  <span className="font-normal text-white/50">
                    ({b.medio_pago})
                  </span>
                </p>
                {b.dias && b.dias.length > 0 && (
                  <p className="mt-0.5 text-xs text-white/50">
                    Días: {resumirDias(b.dias)}
                  </p>
                )}
                {b.condiciones && (
                  <p className="mt-0.5 text-xs text-white/50">
                    {b.condiciones}
                  </p>
                )}
              </div>
              <span className="shrink-0 text-lg font-semibold text-white">
                {formatoValor(b)}
              </span>
            </div>
          ))}
        </div>

        <div className="mt-4 border-t border-hairline-dark pt-4 text-xs text-white/40">
          {comercio.beneficios[0]?.vigencia_hasta && (
            <p>Vigencia: hasta {new Date(comercio.beneficios[0].vigencia_hasta).toLocaleDateString("es-CL")}</p>
          )}
          {(comercio.beneficios[0]?.url || comercio.beneficios[0]?.fuente) && (
            <p className="mt-1">
              Fuente:{" "}
              <a
                href={comercio.beneficios[0].url || comercio.beneficios[0].fuente!}
                target="_blank"
                rel="noopener noreferrer"
                className="underline hover:text-white/60"
              >
                {comercio.beneficios[0].url || comercio.beneficios[0].fuente}
              </a>
            </p>
          )}
          {comercio.beneficios[0]?.actualizado_en && (
            <p className="mt-1">Actualizado {haceTiempo(comercio.beneficios[0].actualizado_en)}</p>
          )}
        </div>
      </div>
    </div>
  );
}
