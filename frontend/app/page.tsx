import { supabase } from "@/lib/supabase";
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

// Un beneficio aplica hoy si su lista de días está vacía (siempre) o incluye hoy.
function aplicaHoy(b: BeneficioDetalle, hoy: string): boolean {
  if (!b.dias || b.dias.length === 0) return true;
  return b.dias.map((d) => d.toLowerCase()).includes(hoy);
}

async function getBeneficiosDeHoy(): Promise<ComercioConBeneficios[]> {
  const { data, error } = await supabase
    .from("beneficio_detalle")
    .select("*")
    .returns<BeneficioDetalle[]>();

  if (error || !data) return [];
  const hoy = diaDeHoy();
  return agruparPorComercio(data.filter((b) => aplicaHoy(b, hoy)));
}

function formatoValor(b: BeneficioDetalle): string {
  if (b.tipo === "porcentaje") return `${b.valor}%`;
  if (b.tipo === "monto") return `$${b.valor}`;
  return `$${b.valor}`;
}

export default async function Home() {
  const comercios = await getBeneficiosDeHoy();
  const hoy = diaDeHoy();

  return (
    <main className="mx-auto max-w-5xl px-4 py-6">
      <header className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-bold">💳 Beneficios de hoy</h1>
      </header>

      <p className="mb-6 text-sm capitalize text-gray-500">📅 {hoy}</p>

      {comercios.length === 0 ? (
        <p className="rounded-lg border border-dashed border-gray-300 p-6 text-center text-gray-500">
          No hay beneficios cargados todavía. Configura Supabase y corre el
          scraper para poblar la base de datos.
        </p>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {comercios.map((c) => (
            <article
              key={c.comercio}
              className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm"
            >
              <div className="mb-2 flex items-start justify-between">
                <h2 className="font-semibold">{c.comercio}</h2>
                <span className="rounded bg-gray-100 px-2 py-0.5 text-xs uppercase text-gray-500">
                  {c.categoria}
                </span>
              </div>
              <ul className="space-y-1 text-sm">
                {c.beneficios.map((b) => (
                  <li key={b.id} className="flex justify-between">
                    <span>
                      {b.tarjeta}{" "}
                      <span className="text-gray-400">({b.medio_pago})</span>
                    </span>
                    <span className="font-medium">{formatoValor(b)}</span>
                  </li>
                ))}
              </ul>
              {c.beneficios[0].condiciones && (
                <p className="mt-2 text-xs text-gray-500">
                  {c.beneficios[0].condiciones}
                </p>
              )}
            </article>
          ))}
        </div>
      )}
    </main>
  );
}
