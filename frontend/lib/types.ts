// Tipos compartidos del dominio. Reflejan la vista `beneficio_detalle`.

export type Categoria = "super" | "farmacia" | "comida" | "combustible";
export type MedioPago = "credito" | "debito";
export type TipoBeneficio = "porcentaje" | "monto" | "precio_fijo";

export interface BeneficioDetalle {
  id: number;
  comercio: string;
  categoria: Categoria;
  tipo: TipoBeneficio;
  valor: number;
  medio_pago: MedioPago;
  dias: string[];
  condiciones: string | null;
  vigencia_desde: string | null;
  vigencia_hasta: string | null;
  fuente: string | null;
  actualizado_en: string;
  tarjeta_id: number;
  tarjeta: string;
  emisor: string | null;
}

// Beneficios agrupados por comercio (como los muestra la UI: una card por comercio).
export interface ComercioConBeneficios {
  comercio: string;
  categoria: Categoria;
  beneficios: BeneficioDetalle[];
}

export function agruparPorComercio(
  items: BeneficioDetalle[]
): ComercioConBeneficios[] {
  const mapa = new Map<string, ComercioConBeneficios>();
  for (const b of items) {
    const grupo = mapa.get(b.comercio);
    if (grupo) {
      grupo.beneficios.push(b);
    } else {
      mapa.set(b.comercio, {
        comercio: b.comercio,
        categoria: b.categoria,
        beneficios: [b],
      });
    }
  }
  return [...mapa.values()];
}
