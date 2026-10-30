# Brasaland website

Public website for Brasaland customers: the landing page and the Brasa Points registration form.

It addresses the Marketing and Digital Experience needs in `CONTEXT.md`: an outdated website and a loyalty programme that generates no customer data.

> _Spanish version: [README.es.md](./README.es.md)._

## Stack

Next.js 16 (App Router), React 19, TypeScript, and Tailwind CSS 4. It is an independent project: it shares no layout with `uis/backoffice`.

## How to run it

```bash
npm install
npm run dev     # http://localhost:3000
npm run lint
npm run build
```

No environment variables are needed.

## Routes

| Route | Content |
|---|---|
| `/` | Landing page: hero, history, features, locations, Brasa Points, and contact |
| `/registro` | Three-step Brasa Points registration form |

## Structure

- `app/`: routes, root layout, and global styles.
- `components/`: one component per section or form piece.
- `hooks/useRegistrationForm.ts`: form steps, values, errors, and submission.
- `lib/locations.ts`: countries, cities, and sites, used by the landing page and the form.
- `lib/registration-validation.ts`: validation rules as pure functions.
- `lib/api.ts`: form submission.
- `public/media/`: images.

## Known limitations

These must be resolved before publishing:

- **Simulated submission:** `submitRegistration()` in `lib/api.ts` does not save or send data, yet the form shows a thank-you message. It will call the FastAPI backend when that exists.
- **No programme terms:** the form requires accepting terms whose text does not exist yet.
- **Placeholder data:** addresses, phone numbers, and map links in `lib/locations.ts` are examples. The footer social links are placeholders too.
- **Unconfirmed rule:** `CONTEXT.md` does not define the "1 point per $10,000 COP" rule shown on the landing page.
- **Broken "Menú" link:** it points to `#menu`, and that section does not exist.
- **Missing favicon:** `favicon.ico` returns 404.
- **Phone error message:** it asks for 10 digits, but the validation accepts 8 to 15.
