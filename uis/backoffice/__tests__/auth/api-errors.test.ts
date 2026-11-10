// Reparto de los errores de la API entre los campos del formulario (lib/auth/api-errors.ts) y el
// error legible a partir del código de estado (errorFromStatus, lib/api-client.ts).
import { ApiError, errorFromStatus } from "@/lib/api-client";
import { formErrorsFromApi } from "@/lib/auth/api-errors";

const REGISTER_FIELDS = ["email", "password", "name"] as const;
const FALLBACK = "No se pudo crear la cuenta. Inténtalo de nuevo.";

describe("formErrorsFromApi", () => {
  it("pone cada detalle de un 422 junto a su campo", () => {
    const error = new ApiError("Los datos no son válidos.", 422, "invalid_request", [
      { field: "email", message: "No es un email válido." },
      { field: "password", message: "La contraseña debe tener al menos 8 caracteres." },
    ]);

    expect(formErrorsFromApi(error, REGISTER_FIELDS, FALLBACK)).toEqual({
      fields: { email: "No es un email válido.", password: "La contraseña debe tener al menos 8 caracteres." },
      message: "Revisa los campos marcados.",
    });
  });

  it("un email duplicado (409) se muestra junto al campo email", () => {
    const error = new ApiError("Ya existe un usuario con el email ana@brasaland.com.", 409, "duplicate_email");

    expect(formErrorsFromApi(error, REGISTER_FIELDS, FALLBACK)).toEqual({
      fields: { email: "Ya existe un usuario con el email ana@brasaland.com." },
      message: null,
    });
  });

  it("los detalles sin campo en el formulario se añaden al mensaje general", () => {
    const error = new ApiError("Los datos no son válidos.", 422, "invalid_request", [
      { field: "email", message: "No es un email válido." },
      { field: "role", message: "Campo no permitido." },
    ]);

    expect(formErrorsFromApi(error, REGISTER_FIELDS, FALLBACK)).toEqual({
      fields: { email: "No es un email válido." },
      message: "Los datos no son válidos. Campo no permitido.",
    });
  });

  it("un error que no es de la API nunca muestra su texto técnico", () => {
    expect(formErrorsFromApi(new TypeError("Failed to fetch"), REGISTER_FIELDS, FALLBACK)).toEqual({
      fields: {},
      message: FALLBACK,
    });
  });
});

describe("errorFromStatus", () => {
  it("un 4xx sin mensaje propio dice qué falló y qué hacer", () => {
    const error = errorFromStatus(404, "no se pudo cargar el perfil");

    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(404);
    expect(error.code).toBe("unknown_error");
    expect(error.message).toBe("No se pudo cargar el perfil. Lo que buscas ya no existe o cambió. Recarga la página.");
  });

  it("un código sin indicación propia usa la genérica", () => {
    expect(errorFromStatus(418, "no se pudo guardar").message).toBe(
      "No se pudo guardar. Inténtalo de nuevo; si el problema continúa, recarga la página."
    );
  });

  it.each([500, 502, 504])("un %i nunca muestra detalles técnicos", (status) => {
    const error = errorFromStatus(status, "no se pudo guardar");

    expect(error.code).toBe("server_error");
    expect(error.message).toBe("El servidor tuvo un problema y no pudo completar la operación. Inténtalo de nuevo en unos minutos.");
  });
});
