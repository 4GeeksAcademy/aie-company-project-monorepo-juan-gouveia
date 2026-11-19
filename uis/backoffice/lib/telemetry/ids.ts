// UUID v4 para `eventId`, `sessionId` y `X-Request-Id`.
//
// crypto.randomUUID solo existe en contextos seguros (HTTPS o localhost): una tablet que abra el
// backoffice por la IP de la red local no lo tiene. crypto.getRandomValues sí está siempre, así que
// se usa como alternativa con el mismo formato.
export function uuidV4(): string {
  const cryptoApi = globalThis.crypto;
  if (typeof cryptoApi?.randomUUID === "function") return cryptoApi.randomUUID();

  const bytes = new Uint8Array(16);
  cryptoApi.getRandomValues(bytes);
  bytes[6] = (bytes[6] & 0x0f) | 0x40; // versión 4
  bytes[8] = (bytes[8] & 0x3f) | 0x80; // variante RFC 4122
  const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}
