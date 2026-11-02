import BrasaPointsCta from "@/components/BrasaPointsCta";

export default function BrasaPoints() {
  return (
    <section
      aria-labelledby="brasapoints-title"
      className="border-b border-red-200 mx-auto max-w-6xl px-3 py-4 md:px-4 lg:px-8"
      id="brasapoints"
    >
      <h2
        id="brasapoints-title"
        className="text-lg font-semibold text-red-700 md:text-xl lg:text-2xl mb-4"
      >
        Brasa Points
      </h2>
      <article className="bg-white rounded-lg p-4 shadow-md">
        <p className="mb-4 text-black md:text-base lg:text-lg">
          Brasa Points es el programa de fidelidad de Brasaland, diseñado para recompensar a
          nuestros clientes más leales.
        </p>

        <h3 className="mb-2 text-md font-semibold text-red-700 md:text-lg lg:text-xl">
          ¿Cómo funciona Brasa Points?
        </h3>

        <ol className="ml-5 list-decimal list-outside mb-4 marker:text-red-700 marker:font-semibold">
          <li>Te registras aquí ¡Es 100% digital!</li>
          <li>
            Acumulas 1 punto por cada $10.000 COP de consumo en Colombia, o por cada $2 USD en
            Estados Unidos.
          </li>
          <li>Canjea tus puntos por descuentos y platos gratis.</li>
          <li>Accede a ofertas exclusivas y promociones especiales, solo para nuestros miembros.</li>
        </ol>

        <BrasaPointsCta />
      </article>
    </section>
  );
}
