# Backoffice de Brasaland

Aplicación interna desde la que el personal de Brasaland accede a sus herramientas en un solo lugar.

Responde a la necesidad de sistemas internos modernos descrita en `CONTEXT.md`. Sus primeras herramientas apoyan la selección de Personas y Cultura y la revisión de la lógica de negocio.

> _Versión en inglés: [README.md](./README.md)._

## Stack

Next.js 16 (App Router), React 19, TypeScript y Tailwind CSS 4. Es un proyecto independiente: no comparte layout con `uis/website`.

## Cómo ejecutarlo

Copia `.env.example` como `.env.local` e indica las URL de las API:

```bash
NEXT_PUBLIC_API_BASE_URL=<url-base-de-la-api>     # API del tracker
API_BASE_URL=http://localhost:8000/api/v1         # API de Brasaland (services/brasaland-api)
```

Las herramientas que usan la API de Brasaland necesitan que esté arrancada; las instrucciones están en [`services/brasaland-api/README.es.md`](../../services/brasaland-api/README.es.md).

Después ejecuta:

```bash
npm install
npm run dev     # http://localhost:3001
npm run lint
npm run build
```

`npm install` enlaza `@repo/brasa-core` desde `packages/brasa-core`, así que hay que ejecutarlo después de clonar el repositorio.

## Sesión

Todas las vistas exigen sesión salvo `/login` y `/register` (ticket AUTH-02). El website público (`uis/website`) no se ve afectado.

| Ruta | Vista |
|---|---|
| `/login` | Email y contraseña (con botón para mostrarla). Guarda el token y vuelve a la ruta de `?next=` (solo rutas internas), o a `/`. Muestra un aviso si la sesión caducó (`?reason=expired`) o la cuenta está desactivada (`?reason=inactive`) |
| `/register` | Email, contraseña (con botón para mostrarla) y perfil opcional (nombre y apellido, teléfono y dirección). Llama a `POST /users` y luego a `POST /auth/login`. Los errores de la API se muestran junto a cada campo |
| `/account/profile` | Requiere sesión. Muestra el email y el perfil (de `GET /auth/me`) y permite editar nombre y apellido, teléfono y dirección con `PUT /profiles/me`. Solo envía los campos cambiados; un campo vacío se borra. Al guardar se actualiza el nombre de la cabecera |

Cómo funciona:

- **Token:** se guarda en `localStorage` (`lib/auth/token.ts`). El cliente común `lib/api-client.ts` lo envía como `Authorization: Bearer <token>` al intermediario, que lo reenvía a la API.
- **Protección:** las vistas protegidas viven en el grupo de rutas `app/(protegido)/`, y toda página creada ahí queda protegida. Su layout usa `SessionProvider`, un guard en el cliente:
  - sin token, redirige a `/login?next=<ruta>`;
  - con token, comprueba la sesión con `GET /auth/me` y no muestra nada hasta tenerla.

  No se usa `proxy.ts`, porque el servidor no puede leer `localStorage`. `useSession()` da acceso al usuario, a `refresh` y a `logout`.
- **Fin de sesión:** ante un 401, o un 403 `inactive_user`, el cliente común borra el token y redirige al login con el motivo. "Cerrar sesión" (en la cabecera) borra el token y lleva a `/login`.
- **Varias pestañas:** si el token desaparece en otra pestaña, esta redirige al login; si cambia, recarga el usuario.

## Herramientas

| Ruta | Herramienta | Datos |
|---|---|---|
| `/` | Portada con una tarjeta por herramienta | `lib/tools.ts` |
| `/talento` | Talent Pipeline Tracker: candidatos, status, stage y notas | API REST |
| `/incidencias` | Análisis de incidencias: sube el CSV de Operaciones, muestra el resumen y los registros inválidos con su motivo, y descarga `results.csv` | API de Brasaland, a través del intermediario |
| `/proveedores` | Directorio de proveedores: listado de activos y suspendidos, filtros por país y categoría, alta, actualización de tarifa y activar o suspender | API de Brasaland (dominio `suppliers`, TinyDB), a través del intermediario |
| `/funciones` | Pruebas manuales de filtros, búsquedas, reportes y validaciones | Datos de ejemplo de `@repo/brasa-core` |

## Añadir una herramienta

1. Crea su ruta en `app/(protegido)/<herramienta>/`, para que exija sesión. El grupo no cambia la URL.
2. Pon sus archivos propios en `components/<herramienta>/` y `lib/<herramienta>/`. Las piezas reutilizables van directamente en `components/`.
3. Añade una entrada en `lib/tools.ts`. La portada y la navegación se generan desde esa lista.

Las áreas internas, incluida la formación, se incorporan aquí como herramientas, no como aplicaciones aparte. Más adelante, cada entrada de `lib/tools.ts` podrá declarar el permiso que necesita y la lista se filtrará con `GET /auth/me`. Ese filtro solo afectará a la interfaz: la autorización real está en la API.

Las llamadas a la API de Brasaland se hacen con `apiJson` o `apiFetch` de `lib/api-client.ts`, que añaden el token, convierten los errores en `ApiError` (`status`, `code`, `message`, `details` por campo) y cierran la sesión ante un 401.

## Estructura

- `app/`: layout raíz (sin cabecera) y dos grupos de rutas:
  - `(protegido)/`: portada y una carpeta por herramienta, con el guard de sesión;
  - `(publico)/`: `login/` y `register/`, con una cabecera sin navegación.
- `app/api/[...path]/route.ts`: intermediario (BFF) hacia la API de Brasaland.
  - Reenvía `GET`, `POST`, `PUT`, `PATCH` y `DELETE` de `/api/<ruta>` a `API_BASE_URL/<ruta>`, con las cabeceras `Content-Type`, `Accept` y `Authorization`, sin aplicar lógica.
  - La URL de la API se queda en el servidor y no hace falta CORS.
  - Si falta la variable responde 500 (`api_not_configured`); si la API no responde, 502 (`api_unavailable`).
- `components/`:
  - componentes base reutilizables, entre ellos `PasswordField`, con botón para mostrar la contraseña, y `FileDropzone`, para cualquier herramienta que reciba archivos;
  - `auth/` (`SessionProvider`, `ProtectedShell`, `AccountMenu` y los formularios de login y registro) y `account/` (perfil);
  - `talento/`, `funciones/`, `incidencias/` y `proveedores/`.
- `hooks/`: hooks personalizados, entre ellos `useSession`.
- `lib/`: `tools.ts`, `format.ts`, `api-client.ts`, `auth/` y una carpeta por herramienta.
- `types/`: tipos de la API (`api.ts` para los errores y `auth.ts` para usuarios y perfiles).

## Limitaciones conocidas

- **El token vive en `localStorage`:** lo exige el ticket AUTH-02, pero un script inyectado en la página podría leerlo. La propuesta de arquitectura (5.2) preveía una cookie inaccesible desde JavaScript.
- **Registro abierto:** `/register` y `POST /users` son públicos, así que cualquiera puede crearse una cuenta `user` y entrar. Aún no hay permisos por herramienta.
- **La comprobación de sesión es del navegador:** el servidor entrega las vistas protegidas sin su contenido, y este solo aparece tras validar el token con la API. La protección real de los datos está en la API.
- **`/funciones` es temporal:** prueba las reglas de `@repo/brasa-core`, un paquete transitorio. Cuando esas reglas pasen al backend, debe retirarse o llamar a la API. No añadas cálculos de negocio a los frontends.
- **`/incidencias` descarga el último análisis de la API:** se guarda en memoria, así que si la API se reinicia hay que volver a subir el archivo, y si dos personas analizan a la vez, se descarga el más reciente.
- **`/proveedores` escribe en la base local de la API:** las altas y los cambios de tarifa o estado se guardan en `services/brasaland-api/storage/brasaland-db.json`. Para volver a los datos iniciales, borra ese archivo y reinicia la API. La interfaz no ofrece borrar proveedores: el flujo habitual es suspenderlos.
- **Altura de la cabecera:** `FilterBar` depende de su altura fija (57 px en móvil y 89 px desde `md`). En móvil no se muestran los enlaces a herramientas; se navega desde la portada. Por debajo de `xl`, "Mi perfil" y "Cerrar sesión" se muestran solo como iconos.
- **API compartida:** el tracker usa una API de playground compartida, así que evita escrituras de prueba. Esa API es de terceros y no recibe el token de sesión.
- **Tras mover rutas, `tsc` puede fallar con tipos antiguos de `.next`:** se arregla borrando `.next`, que es un artefacto generado.
