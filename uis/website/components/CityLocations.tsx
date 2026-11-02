import type { City } from "@/lib/locations";

interface CityLocationsProps {
  city: City;
  mapsNoteId: string;
}

export default function CityLocations({ city, mapsNoteId }: CityLocationsProps) {
  const summaryId = `city-${city.slug}-summary`;
  const panelId = `city-${city.slug}-panel`;

  return (
    <details className="group mb-3 last:mb-0 rounded-lg border border-red-200 bg-white">
      <summary
        id={summaryId}
        className="flex cursor-pointer list-none items-center justify-between rounded-lg p-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-700 focus-visible:ring-offset-2 [&::-webkit-details-marker]:hidden"
        aria-controls={panelId}
      >
        <span className="text-md font-semibold text-red-700 md:text-md lg:text-lg">
          {city.name}
        </span>
        <span className="flex items-center gap-2 text-sm font-medium text-red-700">
          <span className="sr-only">Mostrar u ocultar ubicaciones de {city.name}</span>
          <span className="group-open:hidden">Ver ubicaciones</span>
          <span className="hidden group-open:inline">Ocultar ubicaciones</span>
          <svg
            className="h-4 w-4 transition-transform duration-200 group-open:rotate-180"
            viewBox="0 0 20 20"
            fill="currentColor"
            aria-hidden="true"
          >
            <path
              fillRule="evenodd"
              d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.94a.75.75 0 011.08 1.04l-4.25 4.51a.75.75 0 01-1.08 0l-4.25-4.51a.75.75 0 01.02-1.06z"
              clipRule="evenodd"
            />
          </svg>
        </span>
      </summary>

      <div id={panelId} role="region" aria-labelledby={summaryId} className="px-3 pb-3">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {city.sites.map((site) => {
            const titleId = `sede-${site.id}-title`;

            return (
              <div
                key={site.id}
                className="border border-red-200 rounded-lg p-3 mb-1"
                role="group"
                aria-labelledby={titleId}
              >
                <p className="mb-1 font-semibold" id={titleId}>
                  Sede {site.name}
                </p>
                <p className="mb-1">{site.address}</p>
                <p className="mb-1">Teléfono: {site.phone}</p>
                <a
                  href={site.mapUrl}
                  aria-describedby={mapsNoteId}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-red-700 hover:underline"
                >
                  Ver en Google Maps
                </a>
              </div>
            );
          })}
        </div>
      </div>
    </details>
  );
}
