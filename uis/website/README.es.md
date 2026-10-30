# Website de Brasaland

Sitio público para los clientes de Brasaland: la landing page y el formulario de registro de Brasa Points.

Responde a las necesidades de Marketing y Experiencia Digital de `CONTEXT.md`: un sitio web desactualizado y un programa de fidelización que no genera datos de clientes.

> _Versión en inglés: [README.md](./README.md)._

## Stack

Next.js 16 (App Router), React 19, TypeScript y Tailwind CSS 4. Es un proyecto independiente: no comparte layout con `uis/backoffice`.

## Cómo ejecutarlo

```bash
npm install
npm run dev     # http://localhost:3000
npm run lint
npm run build
```

No necesita variables de entorno.

## Rutas

| Ruta | Contenido |
|---|---|
| `/` | Landing: hero, historia, cualidades, ubicaciones, Brasa Points y contacto |
| `/registro` | Formulario de registro de Brasa Points, en tres pasos |

## Estructura

- `app/`: rutas, layout raíz y estilos globales.
- `components/`: un componente por sección o pieza del formulario.
- `hooks/useRegistrationForm.ts`: pasos, valores, errores y envío del formulario.
- `lib/locations.ts`: países, ciudades y sedes, usados por la landing y el formulario.
- `lib/registration-validation.ts`: reglas de validación como funciones puras.
- `lib/api.ts`: envío del formulario.
- `public/media/`: imágenes.

## Limitaciones conocidas

Deben resolverse antes de publicar:

- **Envío simulado:** `submitRegistration()` en `lib/api.ts` no guarda ni envía datos, aunque el formulario muestra un mensaje de agradecimiento. Cuando exista el backend FastAPI, llamará a `POST /loyalty/enrollments`, que solo registra al cliente: no crea credenciales de acceso.
- **Sin términos del programa:** el formulario exige aceptar unos términos cuyo texto aún no existe.
- **Datos de ejemplo:** las direcciones, los teléfonos y los enlaces de mapas de `lib/locations.ts` son ejemplos. Los enlaces a redes del pie también.
- **Regla sin confirmar:** `CONTEXT.md` no define las reglas de puntos que muestra la landing (1 punto por cada $10.000 COP o $2 USD). Son un supuesto pendiente de confirmar con Marketing.
- **Enlace "Menú" roto:** apunta a `#menu`, y esa sección no existe.
- **Falta el favicon:** `favicon.ico` da 404.
- **Mensaje de error del teléfono:** pide 10 dígitos, pero la validación acepta de 8 a 15.
