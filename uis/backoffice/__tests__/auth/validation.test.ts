// Reglas de los formularios de autenticación (lib/auth/validation.ts). Deben coincidir con las de la
// API (users/models.py): 8 caracteres como mínimo y 72 bytes como máximo.
import {
  emailError,
  mergeFieldErrors,
  passwordError,
  validateChangePassword,
  validateLogin,
  validateNewPassword,
  validateRegister,
  type FieldErrors,
  type LoginValues,
} from "@/lib/auth/validation";

describe("validateLogin", () => {
  it("acepta email y contraseña escritos", () => {
    expect(validateLogin({ email: "ana@brasaland.com", password: "x" })).toEqual({});
  });

  it("marca los dos campos si están vacíos; un email solo con espacios cuenta como vacío", () => {
    expect(validateLogin({ email: "   ", password: "" })).toEqual({
      email: "Escribe tu email.",
      password: "Escribe tu contraseña.",
    });
  });
});

describe("emailError", () => {
  it("acepta un email válido, aunque tenga espacios alrededor", () => {
    expect(emailError("  ana@brasaland.com ")).toBeNull();
  });

  it.each(["sin-arroba", "ana@", "ana@brasaland", "ana @brasaland.com"])("rechaza %p", (email) => {
    expect(emailError(email)).toBe("No es un email válido.");
  });

  it("pide el email si está vacío", () => {
    expect(emailError("")).toBe("Escribe tu email.");
  });
});

describe("passwordError", () => {
  it.each([
    ["8 caracteres", "a".repeat(8)],
    ["72 bytes", "á".repeat(36)], // cada "á" ocupa 2 bytes en UTF-8
  ])("acepta el límite: %s", (_label, password) => {
    expect(passwordError(password)).toBeNull();
  });

  it.each([
    ["vacía", "", "Escribe una contraseña."],
    ["7 caracteres", "a".repeat(7), "La contraseña debe tener al menos 8 caracteres."],
    ["73 bytes con 37 caracteres", "á".repeat(36) + "a", "La contraseña no puede superar 72 bytes."],
  ])("rechaza una contraseña %s", (_label, password, message) => {
    expect(passwordError(password)).toBe(message);
  });
});

describe("validateRegister", () => {
  it("no exige los datos de perfil", () => {
    expect(validateRegister({ email: "ana@brasaland.com", password: "parrilla-segura", name: "", phone: "", address: "" })).toEqual({});
  });

  it("marca el email y la contraseña no válidos", () => {
    expect(validateRegister({ email: "ana@", password: "corta", name: "", phone: "", address: "" })).toEqual({
      email: "No es un email válido.",
      password: "La contraseña debe tener al menos 8 caracteres.",
    });
  });
});

describe("validateNewPassword", () => {
  it("acepta una contraseña válida repetida igual", () => {
    expect(validateNewPassword({ newPassword: "brasa-nueva-2026", confirmPassword: "brasa-nueva-2026" })).toEqual({});
  });

  it("marca la confirmación si no coincide, antes de llamar a la API", () => {
    expect(validateNewPassword({ newPassword: "brasa-nueva-2026", confirmPassword: "brasa-nueva-2025" })).toEqual({
      confirmPassword: "Las contraseñas no coinciden.",
    });
  });

  it("pide la confirmación si está vacía", () => {
    expect(validateNewPassword({ newPassword: "brasa-nueva-2026", confirmPassword: "" })).toEqual({
      confirmPassword: "Repite la contraseña nueva.",
    });
  });
});

describe("validateChangePassword", () => {
  it("acepta la actual y la nueva confirmada", () => {
    expect(
      validateChangePassword({ currentPassword: "parrilla-segura", newPassword: "brasa-nueva-2026", confirmPassword: "brasa-nueva-2026" })
    ).toEqual({});
  });

  it("pide la contraseña actual y aplica las reglas de la nueva", () => {
    expect(validateChangePassword({ currentPassword: "", newPassword: "corta", confirmPassword: "corta" })).toEqual({
      currentPassword: "Escribe tu contraseña actual.",
      newPassword: "La contraseña debe tener al menos 8 caracteres.",
    });
  });
});

describe("mergeFieldErrors", () => {
  it("los errores de la API tapan a los locales del mismo campo", () => {
    const local: FieldErrors<LoginValues> = { email: "No es un email válido.", password: "Escribe tu contraseña." };
    const api: FieldErrors<LoginValues> = { email: "Ya existe un usuario con ese email." };

    expect(mergeFieldErrors(local, api)).toEqual({
      email: "Ya existe un usuario con ese email.",
      password: "Escribe tu contraseña.",
    });
  });

  it("un error de la API borrado (undefined) no tapa el local (regresión de AUTH-03)", () => {
    expect(mergeFieldErrors<LoginValues>({ email: "No es un email válido." }, { email: undefined })).toEqual({
      email: "No es un email válido.",
    });
  });
});
