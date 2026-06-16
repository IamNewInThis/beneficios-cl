import { supabase } from "@/lib/supabase";
import { type BeneficioDetalle } from "@/lib/types";
import { BeneficiosApp } from "./beneficios-app";

async function getBeneficios(): Promise<BeneficioDetalle[]> {
  const { data, error } = await supabase
    .from("beneficio_detalle")
    .select("*")
    .returns<BeneficioDetalle[]>();
  if (error || !data) return [];
  return data;
}

export default async function Home() {
  const beneficios = await getBeneficios();
  return <BeneficiosApp beneficios={beneficios} />;
}
