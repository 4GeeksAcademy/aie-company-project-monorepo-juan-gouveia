// Lectura del cuerpo JSON de una respuesta correcta (readJson, lib/api-client.ts). Usa el `Response`
// de Node: la respuesta se construye a mano, sin red.
import { ApiError, readJson } from "@/lib/api-client";

function response(body: string, status = 200): Response {
  return new Response(body, { status, headers: { "Content-Type": "application/json" } });
}

describe("readJson", () => {
  it("devuelve el cuerpo JSON de la respuesta", async () => {
    const data = await readJson<{ id: number; name: string }[]>(response('[{"id":1,"name":"Carnes del Valle"}]'));

    expect(data).toEqual([{ id: 1, name: "Carnes del Valle" }]);
  });

  it.each([
    ["una página HTML de un proxy", "<!DOCTYPE html><html><body>Bad Gateway</body></html>"],
    ["JSON cortado a mitad", '[{"id":1,"name":"Carn'],
    ["un cuerpo vacío", ""],
  ])("con %s lanza un ApiError legible, nunca el SyntaxError", async (_label, body) => {
    const error = await readJson(response(body)).catch((err: unknown) => err);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 200, code: "invalid_response" });
    expect((error as ApiError).message).toMatch(/^No se pudo leer la respuesta del servidor/);
  });

  it("si el cuerpo ya se leyó, también lanza el error legible", async () => {
    const res = response('{"ok":true}');
    await res.text();

    await expect(readJson(res)).rejects.toMatchObject({ code: "invalid_response" });
  });
});
