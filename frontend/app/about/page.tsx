export default function AboutPage() {
  return (
    <div className="mx-auto max-w-2xl px-4 py-12 text-sm text-white/70 space-y-6">
      <h1 className="text-xl font-semibold text-white">Acerca de</h1>

      <p>
        <strong className="text-white">Beneficios CL</strong> centraliza en un solo lugar los
        descuentos y beneficios que los bancos chilenos ofrecen a sus tarjetahabientes.
        En vez de revisar el sitio de cada banco por separado, aquí puedes buscar, filtrar y
        comparar todas las ofertas disponibles hoy o durante la semana.
      </p>

      <h2 className="text-base font-semibold text-white">Fuentes</h2>
      <ul className="list-disc space-y-1 pl-5">
        <li>Banco BCI — API pública</li>
        <li>Banco de Chile — API Modyo</li>
        <li>Banco Falabella — GraphQL Contentful</li>
        <li>Mach — Storyblok embebido</li>
        <li>Tenpo — Webflow CMS</li>
        <li>Santander — Playwright headful (local)</li>
      </ul>

      <h2 className="text-base font-semibold text-white">Disclaimer</h2>
      <p>
        Los datos mostrados son obtenidos de fuentes públicas y pueden no estar actualizados
        al momento de la consulta. Siempre verifica los términos y condiciones directamente
        con el banco o comercio emisor. Este sitio no está afiliado a ninguno de los bancos
        ni comercios listados.
      </p>
    </div>
  );
}
