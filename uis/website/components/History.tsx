import Image from "next/image";

export default function History() {
  return (
    <section
      aria-labelledby="nuestra-historia-title"
      className="border-b border-red-200 mx-auto max-w-6xl px-3 py-4 md:px-4 lg:px-8"
      id="nuestra-historia"
    >
      <h2
        className="text-lg font-semibold text-red-700 md:text-xl lg:text-2xl mb-4"
        id="nuestra-historia-title"
      >
        Nuestra Historia
      </h2>
      <div>
        <article className="grid grid-cols-1 gap-8 md:grid-cols-2 bg-white rounded-lg p-4 shadow-md border-b border-red-200 mx-auto max-w-6xl px-3 py-4 md:px-4 lg:px-8 mb-6 md:mb-8">
          <div className="md:mt-4">
            <p className="mb-4 text-black md:text-base lg:text-lg">
              Fundado en Medellín en el 2008, Brasaland comenzó como un sueño familiar: compartir el
              auténtico sabor de la carne a la brasa, con calidad constante y servicio cálido.
            </p>
            <p className="mb-4 text-black md:text-base lg:text-lg">
              Hoy contamos con 14 restaurantes repartidos entre Colombia y Estados Unidos, pero
              mantenemos la misma receta de éxito: productos frescos, técnicas tradicionales, y
              pasión por cada plato que servimos.
            </p>
            <p className="text-black md:text-base lg:text-lg">
              Cada visita a Brasaland es una experiencia culinaria que celebra la tradición de la
              parrilla, donde cada bocado refleja nuestro compromiso con la excelencia y el sabor
              auténtico.
            </p>
          </div>

          <div>
            <figure>
              <Image
                src="/media/fachada-brasaland-medellin.jpg"
                alt="Fachada del primer Brasaland en Medellín"
                width={477}
                height={390}
                sizes="(min-width: 768px) 50vw, 100vw"
                loading="eager"
                className="w-full md:mt-4 rounded-lg shadow-md"
              />
              <figcaption className="mt-2 text-sm text-center text-gray-600">
                Fachada del primer Brasaland en Medellín
              </figcaption>
            </figure>
          </div>
        </article>
      </div>
    </section>
  );
}
