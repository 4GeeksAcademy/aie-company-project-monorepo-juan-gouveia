export interface Site {
  id: string;
  name: string;
  address: string;
  phone: string;
  mapUrl: string;
}

export interface City {
  slug: string;
  name: string;
  sites: Site[];
}

export interface Country {
  slug: string;
  name: string;
  phonePrefix: string;
  cities: City[];
}

export interface Option {
  value: string;
  label: string;
}

export function getCountryOptions(): Option[] {
  return countries.map((country) => ({ value: country.slug, label: country.name }));
}

export function getCityOptions(countrySlug: string): Option[] {
  const country = countries.find((item) => item.slug === countrySlug);
  return (country?.cities ?? []).map((city) => ({ value: city.slug, label: city.name }));
}

export function getFavoriteOptions(countrySlug: string, citySlug: string): Option[] {
  const country = countries.find((item) => item.slug === countrySlug);
  const city = country?.cities.find((item) => item.slug === citySlug);
  return (city?.sites ?? []).map((site) => ({
    value: `bra-${site.id}`,
    label: `Brasaland ${site.name}`,
  }));
}

export function getPhonePrefix(countrySlug: string): string | undefined {
  return countries.find((country) => country.slug === countrySlug)?.phonePrefix;
}

// Datos de ejemplo migrados del sitio anterior: direcciones, teléfonos y mapas no son reales.
export const countries: Country[] = [
  {
    slug: "colombia",
    name: "Colombia",
    phonePrefix: "+57",
    cities: [
      {
        slug: "medellin",
        name: "Medellín",
        sites: [
          {
            id: "med-01",
            name: "Medellín 01",
            address: "Cra. 43A #10A - 50, Medellín",
            phone: "+57 4 1234567",
            mapUrl: "https://goo.gl/maps/medellin-location",
          },
          {
            id: "med-02",
            name: "Medellín 02",
            address: "Av. El Poblado #15-80, Medellín",
            phone: "+57 4 2345678",
            mapUrl: "https://goo.gl/maps/medellin-location-2",
          },
          {
            id: "med-03",
            name: "Medellín 03",
            address: "Calle 10 #40-22, Medellín",
            phone: "+57 4 3456789",
            mapUrl: "https://goo.gl/maps/medellin-location-3",
          },
          {
            id: "med-04",
            name: "Medellín 04",
            address: "Cra. 70 #45-12, Medellín",
            phone: "+57 4 4567890",
            mapUrl: "https://goo.gl/maps/medellin-location-4",
          },
        ],
      },
      {
        slug: "bogota",
        name: "Bogotá",
        sites: [
          {
            id: "bog-01",
            name: "Bogotá 01",
            address: "Cra. 43A #10A - 50, Bogotá",
            phone: "+57 4 1234567",
            mapUrl: "https://goo.gl/maps/medellin-location",
          },
          {
            id: "bog-02",
            name: "Bogotá 02",
            address: "Av. El Poblado #15-80, Bogotá",
            phone: "+57 4 2345678",
            mapUrl: "https://goo.gl/maps/medellin-location-2",
          },
          {
            id: "bog-03",
            name: "Bogotá 03",
            address: "Calle 10 #40-22, Bogotá",
            phone: "+57 4 3456789",
            mapUrl: "https://goo.gl/maps/medellin-location-3",
          },
          {
            id: "bog-04",
            name: "Bogotá 04",
            address: "Cra. 70 #45-12, Bogotá",
            phone: "+57 4 4567890",
            mapUrl: "https://goo.gl/maps/medellin-location-4",
          },
        ],
      },
      {
        slug: "cali",
        name: "Cali",
        sites: [
          {
            id: "cal-01",
            name: "Cali 01",
            address: "Cra. 43A #10A - 50, Cali",
            phone: "+57 4 1234567",
            mapUrl: "https://goo.gl/maps/medellin-location",
          },
          {
            id: "cal-02",
            name: "Cali 02",
            address: "Av. El Poblado #15-80, Cali",
            phone: "+57 4 2345678",
            mapUrl: "https://goo.gl/maps/medellin-location-2",
          },
        ],
      },
    ],
  },
  {
    slug: "estados-unidos",
    name: "Estados Unidos",
    phonePrefix: "+1",
    cities: [
      {
        slug: "miami",
        name: "Miami",
        sites: [
          {
            id: "mia-01",
            name: "Miami 01",
            address: "Cra. 43A #10A - 50, Miami",
            phone: "+57 4 1234567",
            mapUrl: "https://goo.gl/maps/medellin-location",
          },
          {
            id: "mia-02",
            name: "Miami 02",
            address: "Av. El Poblado #15-80, Miami",
            phone: "+57 4 2345678",
            mapUrl: "https://goo.gl/maps/medellin-location-2",
          },
        ],
      },
      {
        slug: "orlando",
        name: "Orlando",
        sites: [
          {
            id: "orl-01",
            name: "Orlando 01",
            address: "Cra. 43A #10A - 50, Orlando",
            phone: "+57 4 1234567",
            mapUrl: "https://goo.gl/maps/medellin-location",
          },
          {
            id: "orl-02",
            name: "Orlando 02",
            address: "Av. El Poblado #15-80, Orlando",
            phone: "+57 4 2345678",
            mapUrl: "https://goo.gl/maps/medellin-location-2",
          },
        ],
      },
    ],
  },
];
