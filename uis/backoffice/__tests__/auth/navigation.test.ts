/**
 * @jest-environment jsdom
 */
// Destino tras el login (lib/auth/navigation.ts). `safeNext` impide las redirecciones abiertas:
// ?next= nunca puede llevar al usuario a otro sitio. jsdom solo hace falta para `currentPath`.
import { currentPath, HOME_PATH, loginUrl, safeNext } from "@/lib/auth/navigation";

describe("safeNext", () => {
  it.each(["/", "/proveedores", "/account/profile?tab=datos", "/incidencias#resumen"])("acepta la ruta interna %p", (next) => {
    expect(safeNext(next)).toBe(next);
  });

  it.each([
    ["URL absoluta", "https://evil.example/login"],
    ["URL relativa al protocolo", "//evil.example"],
    ["barra invertida", "/\\evil.example"],
    ["javascript:", "javascript:alert(1)"],
    ["ruta relativa", "proveedores"],
    ["vacío", ""],
    ["null", null],
    ["undefined", undefined],
  ])("manda a inicio un destino externo o inválido: %s", (_label, next) => {
    expect(safeNext(next)).toBe(HOME_PATH);
  });
});

describe("loginUrl", () => {
  it("incluye el destino interno y el motivo", () => {
    expect(loginUrl("/proveedores?pais=CO", "expired")).toBe("/login?next=%2Fproveedores%3Fpais%3DCO&reason=expired");
  });

  it("descarta un destino externo y deja solo el motivo", () => {
    expect(loginUrl("//evil.example", "inactive")).toBe("/login?reason=inactive");
  });

  it("sin destino ni motivo es /login a secas; el inicio no se añade como destino", () => {
    expect(loginUrl()).toBe("/login");
    expect(loginUrl("/")).toBe("/login");
  });
});

describe("currentPath", () => {
  it("devuelve la ruta actual del navegador con su query", () => {
    window.history.pushState({}, "", "/incidencias?estado=open");

    expect(currentPath()).toBe("/incidencias?estado=open");
  });
});
