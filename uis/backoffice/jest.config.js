// Pruebas unitarias de la lógica TypeScript del backoffice (AUTH-088, decisión T-8).
// En .js y no en .ts: un jest.config.ts exigiría instalar ts-node solo para leer la configuración.

/** @type {import('jest').Config} */
module.exports = {
  // Por defecto, sin navegador. Las pruebas que usan localStorage o window lo piden en su
  // cabecera con `@jest-environment jsdom`.
  testEnvironment: "node",
  roots: ["<rootDir>/__tests__"],
  testMatch: ["**/*.test.ts"],
  transform: {
    "^.+\\.ts$": [
      "ts-jest",
      {
        // Jest ejecuta CommonJS; el resto de opciones sale de tsconfig.json.
        tsconfig: { module: "commonjs", moduleResolution: "node", jsx: "react-jsx" },
      },
    ],
  },
  // Mismo alias que tsconfig.json ("@/*" → raíz del proyecto).
  moduleNameMapper: { "^@/(.*)$": "<rootDir>/$1" },
  // Lógica de autenticación cubierta por AUTH-088.
  collectCoverageFrom: [
    "lib/auth/validation.ts",
    "lib/auth/navigation.ts",
    "lib/auth/token.ts",
    "lib/auth/api-errors.ts",
    "lib/api-client.ts",
  ],
  coverageDirectory: "coverage",
};
