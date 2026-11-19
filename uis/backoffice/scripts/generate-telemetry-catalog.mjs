// Genera lib/telemetry/catalog.ts desde docs/telemetry/event-schemas.json (fuente única de verdad).
//
// Uso: npm run telemetry:catalog   (después de cambiar event-schemas.json)
//
// Solo entran los eventos con `source: "browser"`: son los únicos que emite el backoffice. Para cada
// uno se copian la versión del esquema, las propiedades obligatorias y el allowlist. track() descarta
// los eventos que no cumplen. La prueba __tests__/telemetry/catalog.test.ts falla si el archivo
// generado no coincide con el JSON, así que no puede quedar desactualizado sin que se note.
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const schemasPath = resolve(root, "../../docs/telemetry/event-schemas.json");
const outputPath = resolve(root, "lib/telemetry/catalog.ts");

export function buildCatalog(schemas) {
  const catalog = {};
  for (const [eventType, event] of Object.entries(schemas.definitions.events)) {
    if (event.properties.source.const !== "browser") continue;
    const properties = event.properties.properties;
    catalog[eventType] = {
      version: event.properties.schemaVersion.const,
      required: properties.required,
      allowed: Object.keys(properties.properties),
    };
  }
  return catalog;
}

export function renderCatalog(catalog) {
  return `// ARCHIVO GENERADO por scripts/generate-telemetry-catalog.mjs desde docs/telemetry/event-schemas.json.
// No lo edites a mano: cambia el esquema y ejecuta \`npm run telemetry:catalog\`.
//
// Eventos que emite el backoffice (source: "browser"), con la versión de su esquema, sus propiedades
// obligatorias y su allowlist.

export interface CatalogEntry {
  version: string;
  required: readonly string[];
  allowed: readonly string[];
}

export const TELEMETRY_CATALOG: Readonly<Record<string, CatalogEntry>> = ${JSON.stringify(catalog, null, 2)};
`;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const schemas = JSON.parse(readFileSync(schemasPath, "utf8"));
  const catalog = buildCatalog(schemas);
  writeFileSync(outputPath, renderCatalog(catalog));
  console.log(`${Object.keys(catalog).length} eventos del navegador escritos en lib/telemetry/catalog.ts`);
}
