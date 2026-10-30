import BrasaPointsCta from "@/components/BrasaPointsCta";

export default function Hero() {
  return (
    <section
      id="main-top"
      aria-labelledby="hero-title"
      className="bg-gray-100 mx-auto border-b border-red-200 pt-24 max-w-6xl px-3 py-4 md:px-4 lg:px-8"
    >
      <h1
        id="hero-title"
        className="mb-4 text-xl font-semibold text-red-700 md:text-2xl lg:text-3xl"
      >
        <span className="whitespace-nowrap">El sabor de la brasa,</span>
        <br className="sm:hidden" />
        <span className="whitespace-nowrap"> en cada bocado</span>
      </h1>
      <h2 className="mb-4 text-md text-black md:text-base lg:text-lg font-serif italic">
        Desde 2008 sirviendo las mejores carnes a la brasa en Colombia y Estados Unidos. 14
        ubicaciones, una misma pasión por la calidad y el sabor.
      </h2>

      <BrasaPointsCta />
    </section>
  );
}
