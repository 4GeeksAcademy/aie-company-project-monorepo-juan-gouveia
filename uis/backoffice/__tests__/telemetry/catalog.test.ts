// lib/telemetry/catalog.ts se genera desde docs/telemetry/event-schemas.json. Esta prueba falla si
// alguien cambia el esquema y no regenera el catálogo (npm run telemetry:catalog), o lo edita a mano.
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { TELEMETRY_CATALOG } from "@/lib/telemetry/catalog";
import { uuidV4 } from "@/lib/telemetry/ids";

interface SchemaEvent {
  properties: {
    source: { const: string };
    schemaVersion: { const: string };
    properties: { required: string[]; properties: Record<string, unknown> };
  };
}

const schemas = JSON.parse(readFileSync(resolve(__dirname, "../../../../docs/telemetry/event-schemas.json"), "utf8")) as {
  definitions: { events: Record<string, SchemaEvent> };
};

const MANDATORY = [
  "inbound_order_created",
  "outbound_order_created",
  "stock_waste_registered",
  "stock_threshold_triggered",
  "direct_stock_edit_rejected",
  "ingredient_price_variance_detected",
];

describe("catálogo del backoffice", () => {
  it("coincide con los eventos source: browser de event-schemas.json", () => {
    const expected = Object.fromEntries(
      Object.entries(schemas.definitions.events)
        .filter(([, event]) => event.properties.source.const === "browser")
        .map(([eventType, event]) => [
          eventType,
          {
            version: event.properties.schemaVersion.const,
            required: event.properties.properties.required,
            allowed: Object.keys(event.properties.properties.properties),
          },
        ])
    );
    expect(TELEMETRY_CATALOG).toEqual(expected);
  });

  it("tiene los 34 eventos de la fase de captura, con los 6 obligatorios", () => {
    expect(Object.keys(TELEMETRY_CATALOG)).toHaveLength(34);
    expect(Object.keys(TELEMETRY_CATALOG)).toEqual(expect.arrayContaining(MANDATORY));
  });

  it("ningún allowlist admite datos personales", () => {
    const personal = ["email", "name", "password", "phone", "address", "token"];
    for (const entry of Object.values(TELEMETRY_CATALOG)) {
      expect(entry.allowed.filter((key) => personal.includes(key))).toEqual([]);
    }
  });
});

describe("uuidV4", () => {
  const UUID_V4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

  it("genera UUID v4 distintos", () => {
    const ids = new Set(Array.from({ length: 50 }, uuidV4));
    expect(ids.size).toBe(50);
    for (const id of ids) expect(id).toMatch(UUID_V4);
  });

  it("sin crypto.randomUUID (página servida sin HTTPS) usa getRandomValues con el mismo formato", () => {
    // Se tapa con una propiedad propia; al borrarla vuelve la del prototipo.
    Object.defineProperty(globalThis.crypto, "randomUUID", { value: undefined, configurable: true });
    try {
      expect(uuidV4()).toMatch(UUID_V4);
    } finally {
      delete (globalThis.crypto as { randomUUID?: unknown }).randomUUID;
    }
    expect(typeof globalThis.crypto.randomUUID).toBe("function");
  });
});
