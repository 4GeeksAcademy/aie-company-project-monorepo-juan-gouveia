const SITE_URL = "https://brasaland.com/";

function buildSchema(pageName: string) {
  return {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "WebSite",
        "@id": `${SITE_URL}#website`,
        url: SITE_URL,
        name: "Brasaland",
        inLanguage: "es",
      },
      {
        "@type": "WebPage",
        "@id": `${SITE_URL}#webpage`,
        url: SITE_URL,
        name: pageName,
        isPartOf: { "@id": `${SITE_URL}#website` },
        about: { "@id": `${SITE_URL}#organization` },
        inLanguage: "es",
      },
      {
        "@type": ["Organization", "Restaurant"],
        "@id": `${SITE_URL}#organization`,
        name: "Brasaland",
        url: SITE_URL,
        description: "Cadena de restaurantes de carnes a la brasa en Colombia y Estados Unidos.",
        foundingDate: "2008",
        logo: `${SITE_URL}media/logo-brasaland.png`,
        image: `${SITE_URL}media/fachada-brasaland-medellin.jpg`,
        servesCuisine: ["Carnes a la brasa", "Parrilla", "Cocina colombiana"],
        priceRange: "$$",
        areaServed: [
          { "@type": "Country", name: "Colombia" },
          { "@type": "Country", name: "United States" },
        ],
        contactPoint: [
          {
            "@type": "ContactPoint",
            telephone: "+57-4-123-4567",
            contactType: "customer service",
            areaServed: "CO",
            availableLanguage: ["es", "en"],
          },
          {
            "@type": "ContactPoint",
            telephone: "+1-305-123-4567",
            contactType: "customer service",
            areaServed: "US",
            availableLanguage: ["en", "es"],
          },
        ],
        sameAs: ["https://instagram.com/brasaland", "https://facebook.com/brasaland"],
      },
    ],
  };
}

export default function JsonLd({ pageName }: { pageName: string }) {
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{
        __html: JSON.stringify(buildSchema(pageName)).replace(/</g, "\\u003c"),
      }}
    />
  );
}
