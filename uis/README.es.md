# Carpeta `uis`

Esta carpeta contiene **todos los proyectos con interfaz de usuario** para el proyecto transversal de AI Engineering de la compañía — por ejemplo: un sitio web público, un frontend de panel de administración, una interfaz de ecommerce, portales para clientes, aplicaciones Streamlit/Gradio u otras herramientas sólo-frontend.

Los dos proyectos principales que se almacenan aquí son:

- **`website`** — la presencia web pública de la compañía.
- **`backoffice`** — la aplicación interna de administración. Es el lugar ideal para desarrollar múltiples soluciones dentro de un mismo proyecto: autenticación, gestión de personas, gestión de operaciones, comunicación interna y otras capacidades de back-office.

Organiza `uis/` por **distintas áreas de la compañía** — cada subcarpeta agrupa un ámbito diferente (por ejemplo, web pública frente a operaciones internas) e incluye su propia documentación técnica y funcional.

- **Propósito principal**: centralizar en un único lugar todas las aplicaciones frontend que dan soporte a los casos de uso de la compañía.
- **Recomendación**: documenta en este archivo (o en sub-READMEs) las aplicaciones que vayas añadiendo, su objetivo, tecnología usada y cómo ejecutarlas.

## Aplicaciones

| Aplicación | Objetivo | Tecnología | Puerto en desarrollo |
|---|---|---|---|
| [`website`](./website/README.es.md) | Landing y registro de Brasa Points para clientes | Next.js, React, Tailwind CSS | 3000 |
| [`backoffice`](./backoffice/README.es.md) | Herramientas internas: Talent Pipeline Tracker y pruebas de funciones | Next.js, React, Tailwind CSS | 3001 |

## Docker

Las dos apps corren en un único contenedor `uis`: [`Dockerfile`](./Dockerfile) (Node 22 Alpine, `npm ci` por aplicación) y [`start.sh`](./start.sh), que arranca `website` en el 3000 y `backoffice` en el 3001 con `next dev --webpack`. Se levanta desde la raíz del repositorio con `docker compose up`; ver [Ejecutar con Docker](../README.es.md#ejecutar-con-docker).

> _These instructions are also available in [English](./README.md)._
