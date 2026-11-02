import CityLocations from "@/components/CityLocations";
import { countries } from "@/lib/locations";

const MAPS_NOTE_ID = "maps-new-tab-note-global";

export default function Locations() {
  return (
    <section
      aria-labelledby="ubicaciones-title"
      className="border-b border-red-200 mx-auto max-w-6xl px-3 md:px-4 lg:px-8 py-4"
      id="ubicaciones"
    >
      <h2
        id="ubicaciones-title"
        className="text-lg font-semibold text-red-700 md:text-xl lg:text-2xl mb-4"
      >
        Nuestras Ubicaciones
      </h2>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {countries.map((country) => (
          <article
            key={country.slug}
            className="bg-white rounded-lg p-4 shadow-md"
            aria-labelledby={`ubic-${country.slug}-title`}
          >
            <h3
              className="mb-4 text-md font-semibold text-red-700 md:text-lg lg:text-xl"
              id={`ubic-${country.slug}-title`}
            >
              {country.name}
            </h3>

            {country.cities.map((city) => (
              <CityLocations key={city.slug} city={city} mapsNoteId={MAPS_NOTE_ID} />
            ))}
          </article>
        ))}
      </div>

      {/* Nota global para enlaces externos (evita IDs duplicados) */}
      <span id={MAPS_NOTE_ID} className="sr-only">
        Se abre en pestaña nueva.
      </span>
    </section>
  );
}
