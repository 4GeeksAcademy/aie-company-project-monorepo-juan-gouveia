import Image from "next/image";

const FEATURES = [
  {
    title: "El mismo sabor, dónde sea",
    paragraphs: [
      "Nuestros 14 locales trabajan con rigurosos estándares de calidad y siguiendo las mismas recetas que se ganaron tu corazón.",
      "Además, seleccionamos al detalle cada corte de carne, asegurando frescura y sabor en cada plato.",
    ],
    image: {
      src: "/media/cortes-carne.jpg",
      alt: "Cortes de carne de alta calidad",
      width: 600,
      height: 391,
    },
    cardClassName: "",
  },
  {
    title: "Una experiencia cálida",
    paragraphs: [
      "Somos un restaurante que nace como un sueño de familia, es por eso que nos ocupamos de ofrecer el mejor ambiente para ti y los tuyos en cada visita.",
      "Todo nuestro personal está preparado para prestar un servicio amable y atento, para que tu experiencia sea inolvidable.",
    ],
    image: {
      src: "/media/atencion-calida.jpg",
      alt: "Mesero sonriente mientras atiende a clientes",
      width: 2048,
      height: 1366,
    },
    cardClassName: "mb-auto",
  },
  {
    title: "Rapidez sin sacrificios",
    paragraphs: [
      "En Brasaland nos interesa satisfacer los apetitos de nuestros clientes, y hacerlo sin dejar que el tiempo se interponga.",
      "Por eso nuestras brasas siempre están encendidas y nuestros chefs listos para preparar los platos que te dejarán queriendo volver por más.",
    ],
    image: {
      src: "/media/rapidez-atencion.jpg",
      alt: "Personal de restaurante trabajando rápidamente",
      width: 641,
      height: 397,
    },
    cardClassName: "",
  },
];

export default function Features() {
  return (
    <section
      aria-labelledby="por-que-unicos-title"
      className="border-b border-red-200 mx-auto max-w-6xl px-3 py-4 md:px-4 lg:px-8"
      id="por-que-somos-unicos"
    >
      <h2
        id="por-que-unicos-title"
        className="text-lg font-semibold text-red-700 md:text-xl lg:text-2xl mb-4"
      >
        ¿Qué Nos Hace Únicos?
      </h2>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {FEATURES.map((feature, index) => (
          <article
            key={feature.title}
            className={`${feature.cardClassName} bg-white rounded-lg p-4 shadow-md`.trim()}
          >
            <ol
              start={index + 1}
              className="ml-6 list-decimal list-outside mb-2 marker:text-red-700 marker:font-semibold marker:text-md md:marker:text-lg lg:marker:text-xl"
            >
              <li>
                <h3 className="text-md font-semibold text-red-700 md:text-lg lg:text-xl">
                  {feature.title}
                </h3>
              </li>
            </ol>

            <p className="mb-2">{feature.paragraphs[0]}</p>
            <p>{feature.paragraphs[1]}</p>

            <Image
              src={feature.image.src}
              alt={feature.image.alt}
              width={feature.image.width}
              height={feature.image.height}
              sizes="(min-width: 1024px) 33vw, (min-width: 768px) 50vw, 100vw"
              className="mt-4 w-full rounded-lg shadow-md"
            />
          </article>
        ))}
      </div>
    </section>
  );
}
