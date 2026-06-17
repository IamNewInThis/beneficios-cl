import { supabase } from "@/lib/supabase";
import { type BeneficioDetalle } from "@/lib/types";
import { BeneficiosApp } from "./beneficios-app";

// Supabase/PostgREST devuelve como máximo 1000 filas por request. Con más de
// 1000 beneficios, una sola query deja fuera a las fuentes con ids más altos
// (las últimas insertadas, ej. Tenpo). Paginamos con `.range()` y orden estable
// por id hasta traer todo.
const PAGE_SIZE = 1000;

async function getBeneficios(): Promise<BeneficioDetalle[]> {
  const todos: BeneficioDetalle[] = [];
  for (let desde = 0; ; desde += PAGE_SIZE) {
    const { data, error } = await supabase
      .from("beneficio_detalle")
      .select("*")
      .order("id", { ascending: true })
      .range(desde, desde + PAGE_SIZE - 1)
      .returns<BeneficioDetalle[]>();
    if (error || !data || data.length === 0) break;
    todos.push(...data);
    if (data.length < PAGE_SIZE) break;
  }
  return todos;
}

export default async function Home() {
  const beneficios = await getBeneficios();
  return <BeneficiosApp beneficios={beneficios} />;
}
