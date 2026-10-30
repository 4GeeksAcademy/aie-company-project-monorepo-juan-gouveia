export default function Contact() {
  return (
    <section
      aria-labelledby="contacto-title"
      className="mx-auto max-w-6xl px-3 py-4 md:px-4 lg:px-8"
      id="contacto"
    >
      <h2
        id="contacto-title"
        className="text-lg font-semibold text-red-700 md:text-xl lg:text-2xl mb-4"
      >
        Contacto
      </h2>
      <article className="bg-white rounded-lg p-4 shadow-md">
        <p className="mb-4 text-black md:text-base lg:text-lg">
          Si tienes preguntas, comentarios o deseas comunicarte con nosotros, puedes hacerlo a
          través de estos canales:
        </p>
        <ul className="list-disc list-inside mb-4 marker:text-red-700 marker:font-semibold">
          <li>
            Email:{" "}
            <a href="mailto:hola@brasaland.com" className="text-red-700">
              hola@brasaland.com
            </a>
          </li>
          <li>
            Teléfonos:
            <ul className="list-[circle] list-inside mb-4 pl-5">
              <li>Colombia: +57 4 123 4567</li>
              <li>Estados Unidos: +1 305 123 4567</li>
            </ul>
          </li>
        </ul>
      </article>
    </section>
  );
}
