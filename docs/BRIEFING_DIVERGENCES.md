# Divergencias con los briefings — Brasaland

Registro de cada punto en que la implementación se aparta de un briefing o de la consigna del curso, con su motivo. Sirve para justificar las entregas y para que nadie "corrija" una divergencia que es intencionada.

## Cómo usar este documento

- **Cuándo añadir una entrada:** siempre que una carpeta, ruta, nombre, texto o comportamiento no coincida exactamente con el briefing o la consigna, aunque los valores sean correctos.
- **Qué no se registra aquí:** los valores esperados del briefing (campos, categorías, estados, métricas) deben coincidir siempre. Si no coinciden, es un error que hay que corregir, no una divergencia.
- **Cómo se escribe:** una sección por briefing, con una tabla resumen (qué, briefing o consigna, implementación, motivo) y un apartado por divergencia con sus argumentos y su coste.
- **Dónde más se menciona:** la justificación puede repetirse en el README del módulo afectado, pero este documento es la referencia completa.

## Índice

1. [Procesador de reportes de incidentes](#procesador-de-reportes-de-incidentes) (briefing "Utilidad de Análisis de Datos", Fases 1 y 2)
2. [Directorio de proveedores](#directorio-de-proveedores) (briefing del milestone 09, "Lightweight Storage API")
3. [Autenticación y protección de rutas](#autenticación-y-protección-de-rutas) (ticket AUTH-01)
4. [Autenticación en el frontend](#autenticación-en-el-frontend) (ticket AUTH-02)
5. [Recuperación y cambio de contraseña](#recuperación-y-cambio-de-contraseña) (ticket AUTH-03)
6. [Gestor de incidencias centralizado](#gestor-de-incidencias-centralizado) (briefing "Gestor de Incidencias Centralizado")
7. [Auditoría de gestión de errores](#auditoría-de-gestión-de-errores) (briefing "Auditoría de gestión de errores", rama `feature/error-handling-audit`)
8. [Batería de pruebas de autenticación](#batería-de-pruebas-de-autenticación) (ticket AUTH-088, rama `feature/auth-tests`)
9. [Gestión de inventario con ORM](#gestión-de-inventario-con-orm) (Hito 5, ticket BRD-0512, rama `feature/inventory-orm`)
10. [Inventario en el backoffice](#inventario-en-el-backoffice) (Hito 5, fase frontend, ticket BRD-0512, rama `feature/inventory-frontend`)
11. [Contenedorización del monorepo](#contenedorización-del-monorepo) (ticket #infra-40, rama `feature/dockerize`)
12. [Auditoría de rendimiento de ambos frontends](#auditoría-de-rendimiento-de-ambos-frontends) (consigna "Auditoría de rendimiento — ambos frontends", rama `feature/performance-audit`)
13. [Auditoría de serialización del backend](#auditoría-de-serialización-del-backend) (briefing "Auditoría de serialización", rama `feature/serialization-audit`)
14. [Estrategia de caching](#estrategia-de-caching) (briefing "Caching", rama `feature/caching-optimisation`)
15. [Plan de Telemetría](#plan-de-telemetría) (briefing de Brasaland "Proyectos de Telemetría" y enunciado del RFI, rama `feature/telemetry-plan`)
16. [Captura de eventos de telemetría](#captura-de-eventos-de-telemetría) (enunciado "Sistema de captura", rama `feature/telemetry-capture`)
17. [Almacenamiento de eventos de telemetría](#almacenamiento-de-eventos-de-telemetría) (enunciado "Telemetría — Almacenamiento", rama `feature/telemetry-storage`)
18. [Reporte técnico de telemetría](#reporte-técnico-de-telemetría) (enunciado "Telemetría de tu compañía — Reporte técnico", rama `feature/telemetry-report`)
19. [Pipeline de desempeño de negocio](#pipeline-de-desempeño-de-negocio) (briefing "Pipeline de Desempeño de Negocio" y enunciado de la Parte 1, rama `feature/pipeline-design`)
20. [Pipeline de desempeño de negocio resiliente](#pipeline-de-desempeño-de-negocio-resiliente) (enunciado de la Parte 2, rama `feature/pipeline-implementation`)
21. [Pipeline a producción: subflows, tests y dashboard](#pipeline-a-producción-subflows-tests-y-dashboard) (enunciado de la Parte 3, rama `feature/pipeline-production`)
22. [Script nocturno de telemetría](#script-nocturno-de-telemetría) (ticket #DEV-53, rama `feature/nightly-export`)
23. [Cola de tareas asíncronas](#cola-de-tareas-asíncronas) (ticket #DEV-55, rama `feature/async-tasks`)

---

## Procesador de reportes de incidentes

Los valores del análisis coinciden exactamente con el briefing; las diferencias son de ubicación, rutas y textos, y cada una tiene un motivo. Cubre las dos fases del ejercicio: el script de análisis (Fase 1) y su integración en la plataforma con API y backoffice (Fase 2).

| Qué | Consigna o briefing | Implementación | Motivo principal |
| --- | --- | --- | --- |
| Carpeta del script | `incidents-analysis/` (briefing) | `scripts/incident-report/` | La consigna pide `/scripts` |
| Carpeta del backend | `/services/api` | `services/brasaland-api/` | Propuesta de arquitectura del CTO |
| Rutas de la API | `/api/incidents/...` | `/api/v1/incidents/...` | Versión única de la API (propuesta) |
| Lógica compartida | Extraída a módulos compartidos | Primero en `service.py` de la API; desde el gestor de incidencias, en `packages/shared` | **Resuelta:** ver el apartado 3 |
| Pregunta de exportación | `Export results to CSV? [y / n]` | `¿Deseas exportar los resultados a CSV? [s / n]` | La consigna la pide en español |
| Detalle de inválidos | Solo conteos por regla | Conteos + ID, fila y motivo de cada uno | Criterio "muestra los registros inválidos" |
| Regla de estado | No existe | `invalid_status` | Un estado desconocido no debe contar como válido |

### 1. Ubicación del script: `scripts/incident-report/`

El script está en `scripts/incident-report/` y no en `incidents-analysis/`, como indica el briefing.

- **La consigna manda:** pide "Script de análisis (`/scripts`)", y es lo que se evalúa.
- **Encaja en el monorepo:** la carpeta `scripts/` ya existía y el README raíz la reserva para scripts puntuales y CLIs internos. Una carpeta nueva en la raíz incumpliría la regla de no dejar implementación suelta ahí.
- **Queda registrado:** `scripts/README.md` y `scripts/README.es.md` listan `incident-report/`, que tiene su propio README en los dos idiomas.

El CSV fuente se conserva sin modificar en `data/raw/incidents-brasaland.csv`, y la exportación se escribe en `data/process/results.csv`, ignorado en Git. Si la ruta recibida no existe desde la carpeta actual, el script busca el mismo nombre en `data/raw/`, para que `python analyze.py incidents-brasaland.csv` funcione desde la carpeta del script.

### 2. Backend: `services/brasaland-api/` y rutas bajo `/api/v1`

La consigna pide `/services/api` y las rutas `/api/incidents/...`; se siguió la propuesta de arquitectura del CTO ([`ARCHITECTURE_PROPOSAL.md`](./ARCHITECTURE_PROPOSAL.md)).

- **Es el contrato acordado para todo el backend:** una carpeta por servicio con nombre propio y una sola versión de la API bajo `/api/v1` (secciones 2.2 y 3.1 de la propuesta). `incidents` es el primer dominio implementado; desviarse en él rompería esa coherencia desde el principio.
- **Desde el navegador se ve igual que en la consigna:** el backoffice expone `/api/incidents/analyze` y `/api/incidents/results/export`, y su intermediario (BFF) las reenvía a `/api/v1/incidents/...`.
- **Los criterios de evaluación no mencionan rutas ni carpetas,** solo el comportamiento: que el endpoint devuelva el resumen en JSON, que el export sea un CSV descargable y que los errores usen códigos HTTP apropiados.

La propuesta incorpora el dominio `incidents` al árbol de carpetas (2.3), a las dependencias entre dominios (2.5) y al mapa de rutas (3.3). La justificación también está en `services/brasaland-api/README.md` y `README.es.md`.

### 3. Lógica compartida en `service.py` (resuelta)

> **Actualización (gestor de incidencias):** esta divergencia ya no existe. La consigna del gestor exige que la validación esté en `packages/shared/` y la reutilicen el script y la API, así que las reglas se movieron, sin cambios, al paquete Python [`packages/shared`](../packages/shared/README.es.md) (`brasaland_shared.incidents`). La API lo instala como dependencia local, `service.py` solo lo reexporta y `analyze.py` lo importa añadiendo `packages/shared` a la ruta de Python, igual que antes hacía con la API. Las 32 pruebas del script y las 24 del analizador de la API pasaron sin modificarse. Lo que sigue describe la situación anterior y se conserva como historial.

La validación y el análisis existían una sola vez, en `services/brasaland-api/app/domains/incidents/service.py`; el script y la API la importaban.

- **Qué se extrajo:** las constantes (campos, sedes, categorías, estados, reglas, etiquetas de puntaje y límites) y las funciones `validate_record`, `split_records`, `analyze`, `percentage`, `rounded_average`, `build_export_rows` y `export_csv_text`.
- **Qué queda en el script:** solo la consola (formato del reporte, pregunta de exportación y escritura del archivo).
- **Qué queda en la API:** solo HTTP (lectura del archivo subido, traducción de errores a códigos y formato JSON).
- **El frontend no calcula nada:** muestra lo que devuelve la API y solo tiene los textos de presentación.

**Por qué dentro de la API y no en `packages/`:** la propuesta del CTO establece que el backend es la fuente de verdad de las reglas de negocio. `packages/brasa-core` es un paquete transitorio que no admite reglas nuevas y se retirará cuando sus reglas pasen al backend. Poner la lógica de incidentes ahí iría contra esa decisión.

**Cómo lo usa el script:** añade `services/brasaland-api` a `sys.path` e importa `app.domains.incidents.service`. `service.py` solo usa la librería estándar de Python, así que el script sigue sin necesitar instalación. El coste es que `analyze.py` funciona dentro del repositorio, pero no copiado fuera de él; está documentado en su README.

**Prueba de que la extracción no cambió el comportamiento:** las pruebas del script siguieron pasando sin cambios (hoy son 32), y el CSV que exporta la API es idéntico byte a byte al `results.csv` del script.

### 4. Diferencias con la salida esperada del briefing

Todos los valores numéricos coinciden; el briefing acepta "diferencias menores de formato", y estas son las tres que hay.

**Pregunta de exportación en español.** El bloque del briefing termina en `Export results to CSV? [y / n]:`, y el script pregunta `¿Deseas exportar los resultados a CSV? [s / n]:` porque la consigna la pide en español. Acepta `s`, `si`, `sí`, `y` y `yes`, así que quien responda en inglés también exporta; sin entrada disponible no exporta.

**Sección `INVALID RECORDS DETAIL`.** Bajo el desglose por regla, el script lista cada registro inválido con su ID, su fila y su motivo (por ejemplo `BRS-000044 (row 45): Missing location_id`). El criterio de evaluación pide que el script "detecta, clasifica y muestra los registros inválidos con su tipo de problema", y los conteos solos no muestran cuáles son. Los totales y el CSV exportado no cambian; la API y el backoffice muestran el mismo detalle.

**Regla adicional `invalid_status`.** El briefing define seis reglas, pero ninguna cubre un `status` vacío o distinto de `OPEN`, `CLOSED` y `DISCARDED`, aunque la estructura lo marca como requerido. Sin esta regla, un registro así contaría como válido sin aparecer en ningún estado. Con el CSV del briefing queda en 0, así que la consola y el backoffice no la muestran y la salida coincide; en el CSV exportado aparece con valor 0, como todas las reglas, para que la estructura no cambie entre archivos.

En el backoffice se muestran los códigos exactos del briefing (`CUSTOMER_COMPLAINT`, `OPEN`…), acompañados solo de las descripciones de categoría que trae el propio briefing, y los números con punto decimal (`30.2%`, `3.46 / 5.00`).

### 5. Decisiones de funcionamiento

Estas decisiones no se apartan de la consigna, pero cambian cómo se comporta el sistema y conviene conocerlas.

| Decisión | Motivo | Límite conocido |
| --- | --- | --- |
| El último análisis se guarda en la memoria de la API, detrás de `repository.py` | Aún no hay base de datos y los criterios no piden persistencia; el repositorio se sustituirá por la base de datos sin tocar los endpoints | Si la API se reinicia, el export responde 404 y hay que volver a subir el archivo; si dos personas analizan a la vez, se descarga el más reciente |
| El backoffice llama a la API a través de un intermediario (BFF), `app/api/[...path]/route.ts` | Propuesta 5.2: la URL de la API queda en el servidor (`API_BASE_URL`), no hace falta CORS y el intermediario no aplica lógica | Si la API no responde, devuelve 502 con un mensaje claro |
| El tipo de archivo se valida por la extensión `.csv`, no por el `Content-Type` | Windows envía los CSV como `application/vnd.ms-excel` | Un archivo mal nombrado se rechaza después, por no estar en UTF-8 o no tener las columnas esperadas (422) |
| Tamaño máximo de 5 MB | Un mes de incidentes de las 14 sedes ocupa decenas de KB | Archivos mayores reciben 413 |
| Un registro que rompe varias reglas suma en cada una y una sola vez en el total de inválidos | El briefing pide contar cuántos registros caen en cada regla | Los conteos por regla pueden sumar más que el total; la consola y el backoffice lo advierten |
| Las categorías, estados y puntajes se calculan solo con registros válidos | Es lo que muestra la salida esperada (96 válidos, porcentajes sobre 96) | — |
| Entorno virtual propio de la API (`services/brasaland-api/.venv`) | Aísla FastAPI y sus dependencias del Python global | Hay que crearlo antes de arrancar la API (README del servicio) |
| Sin autenticación todavía | No es parte de este ejercicio | El backoffice no debe publicarse hasta que exista el login |

### 6. Cómo verificarlo

Todo lo de esta tabla se ejecutó el 3 de noviembre de 2026 con el CSV del briefing, `data/raw/incidents-brasaland.csv`.

| Qué se comprueba | Comando o acción | Resultado |
| --- | --- | --- |
| Pruebas del script | `cd scripts/incident-report && python -m unittest` | 32 pruebas pasan |
| Pruebas de la API | `cd services/brasaland-api && .venv\Scripts\python -m pytest` | 24 pruebas pasan |
| Script con la ruta como argumento | `python scripts/incident-report/analyze.py data/raw/incidents-brasaland.csv` (también desde otra carpeta, con ruta absoluta) | 100 / 96 / 4; categorías 29, 17, 22, 19, 9; estados 32, 50, 14; puntajes 4, 6, 12, 19, 9; promedio 3.46 |
| Exportación del script | Responder `s` a la pregunta final | `data/process/results.csv` con 26 métricas y las columnas `metric`, `value`, `percentage` |
| Misma lógica en script y API | Comparar el export de la API con el del script | Idénticos byte a byte |
| Errores de la API | Subir un archivo inválido a `POST /api/v1/incidents/analyze` | Sin archivo 400, `.txt` 415, vacío 400, más de 5 MB 413, no UTF-8 422, faltan columnas 422, solo encabezado 422; export sin análisis 404 |
| Backoffice | Arrancar la API (puerto 8000) y `npm run dev` en `uis/backoffice` (puerto 3001); abrir `http://localhost:3001/incidencias` | Carga del CSV, resumen, aviso de los 4 inválidos con su detalle y descarga de `results.csv`; con la API apagada, aviso de servicio no disponible. Revisado y aprobado en el navegador |

---

## Directorio de proveedores

El modelo, las categorías, los estados y los 15 proveedores del seeder coinciden exactamente con el briefing; las pruebas lo comprueban campo a campo. Las diferencias son de ubicación, rutas y decisiones de funcionamiento, y cada una tiene un motivo. Cubre la API (FastAPI + TinyDB + Pydantic) y la página del backoffice.

| Qué | Consigna o briefing | Implementación | Motivo principal |
| --- | --- | --- | --- |
| Ruta del ejercicio | `09-lightweight-storage/` (briefing) | Dominio en `services/brasaland-api/` y página en `uis/backoffice/` | Monorepo por capas; la rúbrica pide `services/` y `uis/backoffice` |
| Carpeta del backend | `services/api/` | `services/brasaland-api/` | Un solo backend (propuesta del CTO), igual que `incidents` |
| Archivos del backend | `main.py`, `models.py`, `database.py`, `routes/suppliers.py`, `seed.py` en la raíz de la API | `app/main.py` y `app/domains/suppliers/{models,database,router,seed}.py` | Organización por dominios; se conservan los nombres de la consigna |
| Rutas de la API | `/suppliers` | `/api/v1/suppliers` | Versión única de la API (propuesta) |
| Página del frontend | `uis/application/app/suppliers/` | `uis/backoffice/app/proveedores/` | La aplicación interna es el backoffice; rutas en español como `/talento` e `/incidencias` |

### 1. Ubicación: un dominio de `services/brasaland-api/`

La consigna dibuja una API nueva en `services/api/`, con sus archivos en la raíz, y una aplicación en `uis/application/`. Se integró en lo que ya existe:

- **Un solo backend:** la propuesta de arquitectura establece una API central organizada por dominios (secciones 2.2 y 2.3). Una segunda API por ejercicio duplicaría el entorno virtual, el puerto, el formato de errores y la configuración.
- **Los nombres de la consigna se conservan** dentro del dominio, para que cada pieza pedida sea fácil de encontrar:

  | Consigna | Implementación |
  | --- | --- |
  | `main.py` (aplicación FastAPI) | `app/main.py`, que registra el router y siembra al arrancar |
  | `models.py` (modelos Pydantic) | `app/domains/suppliers/models.py` |
  | `database.py` (inicialización de TinyDB) | `app/domains/suppliers/database.py` |
  | `routes/suppliers.py` (endpoints) | `app/domains/suppliers/router.py`, como en `incidents` |
  | `seed.py` (carga inicial) | `app/domains/suppliers/seed.py`, que se ejecuta con `uv run seed` |

- **Piezas añadidas por el patrón de dominios:** `repository.py` es lo único que habla con TinyDB, así que migrar a Postgres solo cambiará ese archivo y `database.py`. También se añadieron `exceptions.py` y `dependencies.py`.
- **La rúbrica respalda la ubicación:** pide "`services/` para el backend, `uis/backoffice` para el frontend".

### 2. Rutas bajo `/api/v1`

Es la misma decisión que en el procesador de incidentes ([apartado 2](#2-backend-servicesbrasaland-api-y-rutas-bajo-apiv1)): una sola versión de la API para todo el backend. Desde el navegador las rutas se ven como en la consigna: el backoffice llama a `/api/suppliers` y su intermediario (BFF) las reenvía a `/api/v1/suppliers`. Para ello el intermediario reenvía ahora también `PATCH` y `DELETE`.

### 3. Página en `/proveedores`

La consigna pide `uis/application/app/suppliers/`. La aplicación interna de Brasaland es `uis/backoffice`, donde cada herramienta tiene su carpeta en `app/` y una entrada en `lib/tools.ts`, y sus rutas están en español (`/talento`, `/incidencias`). La página aparece en el menú y en la portada como "Directorio de proveedores". Los valores se muestran con los códigos exactos del briefing (`active`, `carne`, `COP`…).

### 4. Decisiones de funcionamiento

Estas decisiones no se apartan de la consigna, pero concretan lo que no especifica.

| Decisión | Motivo | Límite conocido |
| --- | --- | --- |
| El `id` es el `doc_id` de TinyDB, calculado con lo que hay en el archivo en cada alta | La consigna pide el "ID asignado por TinyDB". Calcularlo sin la caché de TinyDB evita IDs repetidos si `uv run seed` escribe con la API arrancada | Si se borra el proveedor con el ID más alto, su ID se reutiliza (TinyDB hace lo mismo) |
| `updated_at` se fija al crear y en cada `PATCH /rate`; `PATCH /status` no lo cambia | El briefing lo define como "timestamp de la última actualización de tarifa" | No registra cuándo se suspendió un proveedor |
| El cliente no puede enviar `id`, `updated_at` ni campos desconocidos (422) | "`updated_at` es generado por el sistema, no enviado por el cliente" | — |
| Nombre duplicado: 409 `duplicate_supplier`, sin distinguir mayúsculas ni espacios extremos | El problema del briefing son las versiones duplicadas; el seeder ya usa el nombre como clave | Dos proveedores distintos con el mismo nombre comercial necesitarían diferenciarse en el nombre |
| `DELETE` responde 200 con el proveedor eliminado | La rúbrica pide 200/201 en las operaciones exitosas | — |
| La API siembra al arrancar solo si la tabla está vacía; `uv run seed` inserta los que falten por nombre | El CTO no quiere una demo vacía, y un proveedor borrado con `DELETE` no debe reaparecer al reiniciar | Para restaurar un proveedor borrado hay que ejecutar `uv run seed` |
| La moneda debe corresponder al país (422 en `currency`) y el formulario la deriva del país | Restricción de negocio del briefing | — |
| Los errores 422 incluyen `details` con el campo y el motivo en español | El formulario muestra el error de la API, y así se entiende qué corregir | Los mensajes de los enums muestran los valores entre comillas, como Pydantic |
| La base es `storage/brasaland-db.json` (ignorada en Git), configurable con `BRASALAND_DB_PATH` | Son datos locales; las pruebas usan una base temporal | — |
| uv como gestor del servicio, con `uv.lock` versionado | La consigna exige `uv run seed` | Hay que instalar uv (`winget install --id astral-sh.uv -e`); pip sigue funcionando sin las versiones fijadas |
| La interfaz no ofrece borrar | El briefing dice que lo habitual es suspender y que `DELETE` es para corregir datos | Las correcciones se hacen con la API (`/docs`) |
| Los filtros se aplican en la API (`?country=&category=`) y se pueden combinar | Responde a "¿qué proveedores de carne tenemos activos en USA?" | El filtro por estado se hace a la vista, con el badge de cada fila |

### 5. Cómo verificarlo

Todo lo de esta tabla se ejecutó el 3 de noviembre de 2026.

| Qué se comprueba | Comando o acción | Resultado |
| --- | --- | --- |
| Pruebas de la API | `cd services/brasaland-api && uv run pytest` | 132 pruebas pasan (24 de `incidents` y 108 de `suppliers`) |
| Seeder | `uv run seed` dos veces | "15 proveedores insertados, 0 ya existían" y después "0 insertados, 15 ya existían" |
| Seed al arrancar | Arrancar la API con una base vacía | El log muestra "Directorio de proveedores sembrado: 15 proveedores insertados" |
| Persistencia | Cambiar una tarifa y un estado, y reiniciar uvicorn | Los cambios siguen ahí y no se vuelve a sembrar |
| Endpoints | curl a `/api/v1/suppliers` | Filtro USA + carne devuelve Miami Meat; alta 201 con `id`; nombre duplicado 409; tarifa 0, estado `deleted`, país desconocido y USA con COP dan 422; ID inexistente 404 en GET, PATCH y DELETE |
| Backoffice | `tsc`, `lint` y prueba en `http://localhost:3001/proveedores` con la API arrancada | Sin errores. Listado, filtros sin recargar, alta con errores de la API, tarifa, activar/suspender y badges. Revisado en el navegador |

---

## Autenticación y protección de rutas

Ticket AUTH-01: usuarios (solo credenciales), perfiles uno a uno, login con JWT, la dependencia `get_current_user` y su aplicación a las rutas no públicas. Los modelos, los roles (`admin`, `manager`, `user`), los campos y los nombres (`get_current_user`, `user_uuid`, `ACCESS_TOKEN_EXPIRE_MINUTES`) coinciden con el briefing. Las diferencias son de rutas y de decisiones de seguridad que el briefing no concreta.

> **Estado:** implementado y verificado. Exigen token todas las rutas salvo `POST /auth/login`, `POST /users` y `GET /health`, incluidas las 8 rutas existentes de `incidents` y `suppliers` (el briefing pide al menos 5).

| Qué | Briefing | Implementación | Motivo principal |
| --- | --- | --- | --- |
| Rutas | `/auth`, `/users`, `/profiles` | `/api/v1/auth`, `/api/v1/users`, `/api/v1/profiles` | Versión única de la API, como `incidents` y `suppliers` |
| Formato del login | Acepta `email` y `password` | JSON `{email, password}` **y** formulario `username`/`password` | El botón «Authorize» de `/docs` (`OAuth2PasswordBearer`) envía un formulario |
| `role` en el registro | "Los registros nuevos vía `POST /users` usan `user` por defecto" | `POST /users` rechaza `role` (422); el primer admin se crea con `uv run create-admin` | Si el registro público aceptara `role`, cualquiera podría hacerse admin |
| `GET /users` | "Listar todos los usuarios (protegida)" | Solo admin (403 para el resto) | Listar todas las cuentas expone credenciales (emails) ajenas |
| Almacenamiento | `User` y `Profile` en TinyDB | TinyDB en un archivo propio, `storage/auth-db.json` | No interferir con el archivo de proveedores |

### 1. Rutas bajo `/api/v1`

Es la misma decisión que en los ejercicios anteriores ([incidentes, apartado 2](#2-backend-servicesbrasaland-api-y-rutas-bajo-apiv1) y [proveedores, apartado 2](#2-rutas-bajo-apiv1)). El criterio "las rutas de auth están bajo `/auth`, las de usuarios bajo `/users` y las de perfil bajo `/profiles`: estructura limpia y coherente" se cumple dentro del prefijo común; mezclar rutas con y sin `/api/v1` sería menos coherente.

### 2. Login con JSON y con formulario

El briefing dice que `POST /auth/login` "acepta `email` y `password`", y también pide usar `OAuth2PasswordBearer`. El diálogo «Authorize» de `/docs` que genera ese esquema envía un formulario con los campos `username` y `password`, que es el estándar de OAuth2. Para cumplir ambas cosas, el mismo endpoint acepta:

- **JSON** `{"email", "password"}`, como dice el briefing;
- **formulario** `username`/`password`, donde `username` es el email, para que el flujo de `/docs` funcione con un clic.

Las respuestas son las mismas en ambos casos. `/docs` documenta los dos formatos.

### 3. El registro no acepta `role`

`POST /users` es público. Si aceptara `role`, cualquiera podría registrarse como `admin`. Por eso:

- el registro siempre crea `role = user` (el valor por defecto del briefing) y responde 422 si se envía `role`;
- el primer administrador se crea desde la consola con `uv run create-admin`, que también promueve a un usuario existente;
- después, un admin cambia roles con `PUT /users/{id}`, como indica el briefing.

### 4. Decisiones de funcionamiento

Estas decisiones no se apartan del briefing, pero concretan lo que no especifica.

| Decisión | Motivo | Límite conocido |
| --- | --- | --- |
| `id` del usuario y del perfil: UUID4 en texto (el `doc_id` de TinyDB queda interno) | Otros módulos lo guardarán como `user_uuid`; un UUID no es enumerable | — |
| El JWT lleva solo `sub` (el `id`), `iat` y `exp`, firmado con HS256 | "El token debe llevar como mínimo el ID del usuario"; el rol se lee de TinyDB en cada petición, así un cambio de rol o una desactivación aplica al momento | No hay revocación de tokens: un token robado vale hasta que caduca, salvo que se desactive o borre la cuenta. Desde AUTH-03, cambiar o restablecer la contraseña también lo invalida ([apartado 4](#4-invalidación-del-token-y-cierre-de-sesiones)) |
| `SECRET_KEY` y `ACCESS_TOKEN_EXPIRE_MINUTES` son obligatorias y sin valor por defecto; la API no arranca sin ellas | "Se leen desde variables de entorno, no están hardcodeadas" | En local se cargan con `uv run --env-file .env` |
| `GET`, `PUT` y `DELETE /users/{id}`: solo la propia cuenta o un admin; 403 aunque el ID no exista | Criterio "acceder o actualizar las credenciales de otro usuario recibe 403"; no revelar qué IDs existen | — |
| `role` e `is_active` solo los cambia un admin (403) | Un usuario no puede darse más permisos | Un admin puede quitarse a sí mismo el rol |
| `PUT` cambia solo los campos enviados | El briefing usa `PUT` para "actualizar campos" | Diverge de la propuesta de arquitectura, que no usa `PUT`; manda el briefing |
| `DELETE /users/{id}` responde 200 con el usuario eliminado y borra su perfil | Igual que en proveedores; el briefing pide borrar el perfil vinculado | — |
| Perfiles por `/profiles/me` y por `/profiles/{user_id}`: leerlo, el dueño o un admin; modificarlo, solo el dueño (403 en otro caso, también para un admin) | "Solo el dueño del perfil puede modificarlo", y el criterio de evaluación pide 403 al acceder o actualizar el perfil de otro usuario | Un admin no edita perfiles ajenos |
| Email único sin distinguir mayúsculas (409 `duplicate_email`) | El email es la credencial de login | — |
| Contraseña de 8 caracteres a 72 bytes | bcrypt rechaza más de 72 bytes; mejor un 422 claro que un 500 | — |
| Login fallido: mismo 401 `invalid_credentials` si el email no existe o la contraseña falla, y bcrypt se ejecuta en ambos casos | No revelar qué emails están registrados | Sin límite de intentos |
| Cuenta desactivada: 403 `inactive_user` en el login y con un token ya emitido | Distinguir "no te conozco" (401) de "te conozco, pero no puedes entrar" (403) | — |
| `/health` sigue siendo pública | Lo usan las comprobaciones de disponibilidad y no expone datos | — |
| `/incidencias` y `/proveedores` del backoffice reciben 401 | El briefing lo da por esperado: el frontend enviará el token en una fase posterior | Resuelto en AUTH-02 ([sección siguiente](#autenticación-en-el-frontend)): con sesión vuelven a funcionar |

### 5. Cómo verificarlo

Todo lo de esta tabla se ejecutó el 4 de noviembre de 2026.

| Qué se comprueba | Comando o acción | Resultado |
| --- | --- | --- |
| Pruebas de la API | `cd services/brasaland-api && uv run pytest` | 361 pruebas pasan: `core` 35, `incidents` 24, `suppliers` 108, `users` 78, `profiles` 30, `auth` 27 y rutas protegidas 59 |
| Configuración | Arrancar sin `.env` y con `uv run --env-file .env` | Sin `.env` la API no arranca y nombra `SECRET_KEY`; con él, `/health` responde 200 |
| Contraseñas | Pruebas de `users` sobre el archivo TinyDB | El texto plano no aparece en el archivo; solo el hash `$2b$` de bcrypt. `name`, `phone` y `address` solo están en `profiles` |
| Flujo completo en `/docs` | Registro con `POST /users` → «Authorize» (o `POST /auth/login` y copiar el token) → `GET /auth/me` y `GET /suppliers` | Revisado por el desarrollador en el navegador |
| 401 | curl a las rutas protegidas sin token, con un token alterado y con uno caducado | 401 con `WWW-Authenticate: Bearer` (`not_authenticated`, `invalid_token`, `token_expired`) |
| 403 | Un usuario lee, cambia o borra la cuenta de otro, lee o cambia el perfil de otro (`/profiles/{user_id}`), o intenta cambiarse el rol | 403 `forbidden`; `GET /users` responde 403 a quien no es admin; un admin lee cualquier perfil pero recibe 403 al modificar uno ajeno |
| Rutas existentes | curl a 6 rutas de `suppliers` e `incidents` con y sin token | Sin token, 401; con token, las respuestas de siempre (200, o 404 en el export sin análisis previo) |
| Ninguna ruta abierta por olvido | `tests/integration/test_protected_routes.py` sobre `/openapi.json` | Solo son públicas `POST /auth/login`, `POST /users` y `GET /health`. Al quitar la protección de `suppliers`, la prueba falla |
| Primer admin | `uv run create-admin` con datos inválidos | Mensaje en español y no escribe nada; los casos válidos están cubiertos por pruebas |

---

## Autenticación en el frontend

Ticket AUTH-02: vistas de login, registro y perfil, protección de las vistas que requieren sesión y ciclo de vida del token en las apps Next.js del monorepo, salvo el website público. Coinciden con el ticket:

- las rutas `/login`, `/register` y `/account/profile`;
- los endpoints que llaman (`POST /users`, `POST /auth/login`, `GET /auth/me`, `PUT /profiles/me`);
- el token en `localStorage` y la cabecera `Authorization: Bearer <token>`;
- el guard en el cliente;
- el comportamiento al cerrar sesión y ante un `401`.

Las diferencias son de camino (el token pasa por el intermediario), de la propuesta de arquitectura y de lo que el ticket no concreta.

> **Estado:** implementado y verificado. Solo hay una app afectada, `uis/backoffice`: es la única app Next.js aparte del website, que sigue intacto.

| Qué | Ticket o propuesta | Implementación | Motivo principal |
| --- | --- | --- | --- |
| Destino de las llamadas | "Adjuntar el token a cada llamada protegida a la API" | El navegador envía el token al intermediario del backoffice (`/api/...`), que lo reenvía a `/api/v1/...` | Mantiene la URL de la API en el servidor, sin CORS; el intermediario sigue sin lógica |
| Dónde vive la sesión | Propuesta 5.2: cookie inaccesible desde JavaScript; el token nunca llega al navegador | `localStorage`, como exige el ticket | Manda el ticket; la propuesta se ha actualizado |
| Cuenta desactivada | Solo se menciona el `401` | Un 403 `inactive_user` también cierra la sesión | La API responde 403 a una cuenta desactivada con un token válido |
| Protección | "Layout guard o hook personalizado" | Grupo de rutas `app/(protegido)/`, cuyo layout es el guard; valida el token con `GET /auth/me` | Toda vista nueva del grupo queda protegida sin acordarse de nada; "no es válido" se comprueba con la API |
| Registro | "Formulario de registro" | Sin campo "Repite la contraseña"; botón para mostrarla (también en el login) | Decisión del desarrollador |

### 1. El token pasa por el intermediario

El backoffice ya llamaba a la API a través de su intermediario (BFF) `app/api/[...path]/route.ts` ([directorio de proveedores](#directorio-de-proveedores)). Para AUTH-02:

- **Lo que cumple del ticket:** el navegador lee el token de `localStorage` y lo envía en `Authorization: Bearer <token>` en cada llamada protegida.
- **Lo que hace el intermediario:** ahora copia la cabecera `Authorization` (antes la descartaba) y reenvía también `PUT`, que necesita `PUT /profiles/me`. No valida el token ni aplica permisos: eso lo hace la API.
- **Por qué no llamar a la API directamente:** obligaría a abrir CORS en la API y a publicar su URL en una variable `NEXT_PUBLIC_`, contra la propuesta (5.3 y 5.4), sin ninguna ventaja para el ticket.
- **Las rutas:** desde el navegador son `/api/auth/login`, `/api/users`, `/api/auth/me` y `/api/profiles/me`. El intermediario las reenvía a `/api/v1/...`, como en los ejercicios anteriores.

### 2. `localStorage` frente a la propuesta de arquitectura

La propuesta (5.2) preveía que el servidor de Next.js guardara la sesión en una cookie `httpOnly` y añadiera el token en el intermediario, de modo que el token nunca llegara al navegador. El ticket exige `localStorage`, y manda el ticket. La propuesta se ha actualizado para reflejarlo.

- **Coste:** un script inyectado en la página (XSS) podría leer el token. Con una cookie `httpOnly` no podría.
- **Lo que lo limita:** el token caduca (`ACCESS_TOKEN_EXPIRE_MINUTES`); la API vuelve a leer el usuario en cada petición, así que desactivar o borrar una cuenta corta el acceso al momento; y la interfaz no inserta HTML de terceros.
- **Sin `proxy.ts`:** el servidor no puede leer `localStorage`, así que la comprobación de sesión se hace en el cliente, como indica el ticket.

### 3. Decisiones de funcionamiento

Estas decisiones no se apartan del ticket, pero concretan lo que no especifica.

| Decisión | Motivo | Límite conocido |
| --- | --- | --- |
| Cliente común `lib/api-client.ts`: añade el token, convierte los errores en `ApiError` (con `details` por campo) y gestiona el 401 | El ticket pide el token "en cada llamada protegida" y el 401 en todas; centralizarlo evita que una herramienta lo olvide | El tracker no lo usa: llama a una API de terceros (playground) que no debe recibir el token |
| El guard valida el token con `GET /auth/me` antes de mostrar nada; sin token, redirige sin llamar a la API | El ticket pide redirigir si el token "está ausente o no es válido"; solo la API sabe si es válido. Además, el usuario se reutiliza en la cabecera y el perfil | Una petición más al entrar en la zona protegida. Si la API está caída, se muestra el error con "Reintentar" en vez de redirigir |
| Tras el login, vuelta a la ruta pedida (`?next=`), o a `/` si no hay | "Redirige a la vista autenticada principal"; un enlace directo no obliga a navegar otra vez | `next` solo admite rutas internas (empieza por `/`, no por `//`), para que no pueda enviar a otro sitio |
| Al expirar la sesión, el login muestra el motivo (`?reason=expired` o `inactive`) | El usuario entiende por qué tiene que volver a entrar | — |
| En el login, un 401 se muestra como "credenciales incorrectas" y no cierra la sesión | Es el único sitio donde un 401 no significa sesión inválida | — |
| Sincronización entre pestañas con el evento `storage` | Cerrar sesión en una pestaña la cierra en todas; con otra cuenta, las demás recargan el usuario | — |
| Registro: si el login automático falla tras crear la cuenta, se muestra "Cuenta creada" con enlace al login | La cuenta ya existe; repetir el registro daría 409 | — |
| Perfil: solo se envían los campos cambiados, y un campo vacío se envía como `null` | `PUT /profiles/me` cambia solo los campos enviados y `null` vacía el campo; así no se pisan datos sin querer | — |
| Por debajo de `xl`, "Mi perfil" y "Cerrar sesión" se muestran como iconos con `aria-label` | `FilterBar` depende de la altura fija de la cabecera, y con 4 herramientas el texto no cabe | El nombre del usuario solo se ve desde `xl` (y al pasar el ratón) |
| Registro abierto | El ticket pide `/register` y `POST /users` es público (AUTH-01) | Cualquiera puede crearse una cuenta `user` y entrar en el backoffice; aún no hay permisos por herramienta |

### 4. Cómo verificarlo

Ejecutado el 4 y el 6 de noviembre de 2026, con la API y el backoffice en local y bases TinyDB temporales (`AUTH_DB_PATH` y `BRASALAND_DB_PATH`).

| Qué se comprueba | Comando o acción | Resultado |
| --- | --- | --- |
| Compilación | `npx tsc --noEmit`, `npm run lint` y `npm run build` en `uis/backoffice` | Sin errores; las URL no cambian con los grupos de rutas |
| API sin regresiones | `cd services/brasaland-api && uv run pytest` | 361 pruebas pasan |
| Website intacto | `git status uis/website` y búsqueda de `localStorage`, `Authorization` y `/login` en `uis/website` | Sin cambios ni rastro de sesión |
| Intermediario y token | curl a `/api/...` del backoffice sin token, con token y con un token alterado | 401 `not_authenticated`; las respuestas normales (15 proveedores, análisis 100/96, export `text/csv`); 401 `invalid_token` |
| Registro | `POST /api/users` con email duplicado, datos inválidos y datos válidos | 409 `duplicate_email`; 422 con `details` de `email` y `password`; 201 y login correcto |
| Perfil | `PUT /api/profiles/me` parcial, con `null`, con un nombre de 121 caracteres y sin token | Cambia solo lo enviado; vacía el campo; 422 con `details.name`; 401 |
| Sin contenido antes de validar | HTML de servidor de `/`, `/proveedores`, `/incidencias`, `/talento`, `/funciones` y `/account/profile` | Solo "Comprobando la sesión...", sin navegación ni contenido |
| Flujos en el navegador | Sin sesión a `/proveedores` → `/login?next=...` → vuelta; registro; perfil y nombre en la cabecera; cerrar sesión (token borrado); dos pestañas; token alterado a mano → `/login?reason=expired` | Revisado por el desarrollador |

---

## Recuperación y cambio de contraseña

Ticket AUTH-03: restablecimiento de la contraseña por correo y cambio con la sesión iniciada, en la API y en el backoffice. Coinciden con el ticket:

- los tres endpoints (`forgot-password`, `reset-password` y `change-password`) y sus cuerpos (`{email}`, `{token, new_password}` y `{current_password, new_password}`);
- los códigos que pide: 200 siempre en `forgot-password` y 400 en `reset-password` y `change-password`;
- las vistas `/forgot-password`, `/reset-password` y `/account/change-password`, y el enlace "¿Olvidaste tu contraseña?" en `/login`;
- el mensaje "Si esa dirección está registrada, recibirás un enlace en breve";
- la caducidad entre 15 y 60 minutos, el token de un solo uso y la API key en una variable de entorno (`RESEND_API_KEY`, documentada en `.env.example` y en el README de la API).

Las diferencias son de rutas, de un endpoint añadido, del cierre de sesiones y de lo que el ticket deja por decidir.

> **Estado:** implementado y verificado. De los opcionales se hicieron la plantilla HTML y el límite por hora; el registro de auditoría no.

| Qué | Ticket | Implementación | Motivo principal |
| --- | --- | --- | --- |
| Rutas | `/auth/forgot-password`, `/auth/reset-password`, `/auth/change-password` | Bajo `/api/v1/auth/...` | Versión única de la API, como en AUTH-01 |
| Proveedor de correo | Resend o SendGrid | Resend, con el remitente `onboarding@resend.dev` | Plan gratuito permanente; funciona sin dominio propio |
| Comprobar el enlace | Solo `POST /auth/reset-password` | También `POST /auth/reset-password/validate`, que lo comprueba sin usarlo | Avisar al abrir un enlace caducado o usado, no después de escribir la contraseña |
| Invalidación del token | Persistir estado en el servidor (uno de tres mecanismos) | JWT con `jti` y la tabla `password_resets`, **más** `password_changed_at` | El primero hace el enlace de un solo uso; el segundo cierra las sesiones abiertas |
| Respuesta de `change-password` | Actualiza la contraseña | Devuelve además un token de acceso nuevo | Las sesiones anteriores dejan de valer, también la actual |
| `forgot-password` con un email mal formado | "Devuelve siempre `200`" | 422 | Es un error de formato; no revela si la cuenta existe |
| Opcionales | Plantilla HTML, límite por hora y auditoría | Plantilla HTML (con versión en texto) y 3 enlaces por cuenta y hora; sin auditoría | Decisión del desarrollador (P-8 y P-9) |
| Código de tickets anteriores | — | Corregidos el `doc_id` de TinyDB (AUTH-01) y los errores por campo del login y el registro (AUTH-02) | Fallos encontrados al probar este ticket |

### 1. Rutas bajo `/api/v1`

Es la misma decisión que en [AUTH-01, apartado 1](#1-rutas-bajo-apiv1): todas las rutas de `auth` viven bajo el prefijo común. El backoffice las llama a través de su intermediario (`/api/auth/...`), que las reenvía a `/api/v1/auth/...`, como en [AUTH-02](#1-el-token-pasa-por-el-intermediario).

### 2. Resend frente a SendGrid

El ticket deja elegir entre los dos. El desarrollador eligió Resend, tras comparar el 6 de noviembre de 2026 la documentación oficial de ambos:

1. **Gratis sin fecha de fin:** 3.000 correos al mes y 100 al día. SendGrid ofrece una prueba de 60 días, y después su plan más barato es de pago. El proyecto se evaluará después de esta entrega, y la prueba podría haber caducado.
2. **Alta más sencilla:** una cuenta y una API key con permiso "Sending access". SendGrid exige una cuenta de Twilio, 2FA y verificar un remitente con una dirección física.
3. **Funciona sin dominio propio:** el remitente `onboarding@resend.dev` es el que propone el propio ticket. Con SendGrid sin dominio, el remitente sería un correo personal (Gmail, Outlook…), y su consola avisa de que esos envíos pueden fallar la comprobación DMARC y no llegar.
4. **Integración simple:** el SDK `resend` lanza una excepción si el envío falla, así que el error se gestiona en un solo sitio (`core/email.py`).

- **Coste:** sin un dominio verificado, Resend solo entrega al email de su cuenta; a cualquier otro destinatario responde 403. Para la demo basta con registrar en Brasaland un usuario con ese email.
- **Cómo se trata el rechazo:** la API lo registra en el log, sin destinatario ni enlace, y al cliente le responde lo mismo (200). Con un dominio propio bastará con verificarlo y cambiar `EMAIL_FROM`; el código no cambia.
- **Sin API key:** la API arranca, avisa en el log y no envía nada. Las pruebas sustituyen el emisor por uno falso, sin llamar a Resend ni gastar cuota.

### 3. Endpoint añadido: `POST /auth/reset-password/validate`

El ticket solo pide que `reset-password` rechace los enlaces no válidos. Así, quien abría un enlace usado o caducado se enteraba después de escribir dos veces la contraseña nueva. En la primera revisión, el desarrollador pidió que se avisara antes.

- **Qué hace:** comprueba la firma, la caducidad, el propósito, que el enlace no se haya usado y que la cuenta siga activa, **sin consumirlo**. Responde 400 con los mismos códigos que `reset-password` (`invalid_reset_token`, `reset_token_expired` y `reset_token_used`).
- **Cómo lo usa el frontend:** `/reset-password` lo llama al abrirse. Si el enlace no sirve, muestra el error y "Solicitar un nuevo enlace" sin enseñar el formulario.
- **El token va en el cuerpo,** no en la URL de la API, para que no quede en los logs de acceso.
- **Si la API no responde:** el formulario sigue disponible con el aviso, porque `reset-password` vuelve a comprobar el enlace al guardar.
- **Es público,** como `forgot-password` y `reset-password`; la prueba de rutas protegidas lo incluye en su lista de rutas públicas.

### 4. Invalidación del token y cierre de sesiones

El ticket avisa de que codificar la expiración en el JWT no basta, y propone tres mecanismos. Se usan dos, porque resuelven problemas distintos:

- **Enlace de un solo uso:** el token del enlace es un JWT con `purpose: "password_reset"` y un `jti`, que tiene una fila en `password_resets`. Al usarlo, la fila se marca y el enlace deja de valer. Usar un enlace anula también los demás enlaces pendientes del usuario, y cambiar la contraseña con sesión, también.
- **Cierre de sesiones (`password_changed_at`):** el ticket deja abierto si cambiar la contraseña cierra las demás sesiones. Se decidió que sí (P-6): tras un restablecimiento o un cambio, la API rechaza con 401 `session_revoked` los tokens de acceso emitidos antes. Quien conociera la contraseña antigua y tuviera una sesión abierta la pierde.
- **Tokens separados:** un token de restablecimiento no sirve como sesión, ni un token de acceso como enlace. Antes de este ticket, `decode_access_token` aceptaba cualquier JWT firmado con `SECRET_KEY`.
- **Por qué `change-password` devuelve un token:** el cierre alcanza también a la sesión desde la que se cambia la contraseña. La respuesta trae un token nuevo; `/account/change-password` lo guarda y el usuario sigue dentro. Las demás pestañas del mismo navegador lo leen de `localStorage`.
- **Límite conocido:** `iat` va en segundos, así que un token emitido en el mismo segundo que el cambio sigue valiendo. Así funciona el token nuevo de `change-password`; la ventana es despreciable.

### 5. `forgot-password` responde 422 a un email mal formado

El ticket pide responder "siempre `200`, se haya encontrado o no el email", para no revelar qué cuentas existen. A un texto que ni siquiera es un email (`no-es-un-email`), la API responde 422, como en el resto de rutas: es un error de la petición, igual para todos, y no dice nada de las cuentas registradas. Con cualquier email bien formado (exista o no, esté inactivo o por encima del límite por hora) la respuesta es la misma: 200 y el mismo mensaje.

### 6. Opcionales: plantilla HTML y límite por hora

- **Plantilla HTML (P-8):** el correo lleva una versión HTML, con un botón y el enlace también en texto, y otra en texto plano para los clientes que no muestran HTML. Es de una columna y con ancho máximo, así que se lee bien en el móvil (lo comprueban las pruebas de `core/test_email.py`).
- **Límite por hora (P-9, opción B):** como máximo 3 enlaces por cuenta y hora. Las solicitudes de más se ignoran en silencio y reciben la misma respuesta, para no revelar nada. Se cuenta por cuenta y no por dirección IP, porque la API aún no tiene un mecanismo común de límite de peticiones.
- **Sin auditoría:** registrar la dirección IP obligaría a que el intermediario reenviara `X-Forwarded-For` y a decidir cuándo fiarse de esa cabecera. `password_resets` ya deja constancia de cuándo se pidió y se usó cada enlace.

### 7. Correcciones en el código de tickets anteriores

Al probar este ticket aparecieron dos fallos en código de AUTH-01 y AUTH-02. Se corrigieron aquí, con la aprobación del desarrollador, porque afectaban al flujo:

- **`doc_id` de TinyDB entre procesos (AUTH-01):** TinyDB guarda en memoria el siguiente `doc_id`. Si otro proceso insertaba en el mismo archivo (por ejemplo, `uv run create-admin` con la API arrancada), la siguiente inserción de la API daba 500. Ahora `app/core/storage.py` (`insert_with_file_id`) calcula el `doc_id` a partir del archivo en los repositorios de usuarios, perfiles y `password_resets`, como ya hacía `suppliers`. Tiene su prueba.
- **Errores por campo en `/login` y `/register` (AUTH-02):** al editar un campo, su error de la API quedaba en `undefined` y tapaba el error local de ese campo. `mergeFieldErrors` (`lib/auth/validation.ts`) solo deja pasar los errores de la API que tienen texto. También lo usan `/reset-password` y `/account/change-password`.

### 8. Decisiones de funcionamiento

Estas decisiones no se apartan del ticket, pero concretan lo que no especifica.

| Decisión | Motivo | Límite conocido |
| --- | --- | --- |
| El correo sale en segundo plano (`BackgroundTasks`), después de responder | Ni la respuesta ni su tiempo revelan si la cuenta existe; un fallo de Resend no llega al cliente | Si el envío falla, solo queda en el log |
| Una cuenta desactivada no recibe enlace (y la respuesta es la misma) | No puede iniciar sesión, así que restablecer la contraseña no le sirve | — |
| `PASSWORD_RESET_EXPIRE_MINUTES`: 30 por defecto; fuera de 15–60, la API no arranca | El ticket fija el rango de 15 a 60 minutos | — |
| El enlace es `<FRONTEND_URL>/reset-password?token=...` | El ticket pide leer el token del query string | `FRONTEND_URL` apunta al backoffice; por defecto, `http://localhost:3001` |
| `/reset-password` no envía la URL como `Referer` (`referrer: no-referrer`) | El token va en la URL; así no llega a otros sitios | — |
| Tras restablecer, `/login?reset=success` muestra el aviso de éxito | El ticket pide redirigir a `/login` "con un mensaje de éxito" | — |
| `/forgot-password` se desactiva tras un 200; si la petición no llega a la API, deja reintentar | El ticket pide evitar envíos duplicados; si falló la red, no se envió nada | — |
| `/account/change-password` está en `(protegido)`, se enlaza desde "Mi perfil" y avisa de que se cerrarán las demás sesiones | Queda protegida como el resto de vistas, y el usuario sabe lo que pasará | — |
| Un 400 de `change-password` se muestra junto a "Contraseña actual" | Es el único campo que puede estar mal | — |
| La contraseña nueva sigue las reglas del registro (de 8 caracteres a 72 bytes) | Mismas reglas en toda la API | No se impide repetir la contraseña actual |

### 9. Cómo verificarlo

Ejecutado el 6 y el 8 de noviembre de 2026, con la API y el backoffice en local y bases TinyDB temporales (`AUTH_DB_PATH` y `BRASALAND_DB_PATH`). Hay una fila por cada criterio de evaluación del ticket, más la de regresiones.

| Criterio | Comando o acción | Resultado |
| --- | --- | --- |
| `forgot-password` envía un correo real con el enlace a una dirección registrada | `POST /auth/forgot-password` con el email de la cuenta de Resend | Correo recibido y revisado por el desarrollador |
| `forgot-password` responde 200 con una dirección no registrada | Prueba `test_forgot_password_answers_the_same_for_unknown_emails` y las del límite por hora; curl con un email no registrado | 200 con el mismo mensaje y tiempos parecidos (83 ms frente a 67 ms) |
| El token caduca tras la ventana configurada | Pruebas `test_expired_reset_token_is_rejected` y `test_token_expires_after_the_configured_window` (ventana de 15 minutos y enlace de hace 16) | 400 `reset_token_expired`; la contraseña no cambia |
| `reset-password` cambia la contraseña e invalida el token | Pruebas de `test_password_router.py`; en vivo, restablecimiento y login | 200; login con la contraseña antigua 401 y con la nueva 200; la sesión anterior da 401 `session_revoked` |
| `reset-password` responde 400 a tokens caducados o usados | `test_reset_token_cannot_be_used_twice` y las de caducidad; en vivo, el mismo enlace dos veces | 400 `reset_token_used` y `reset_token_expired`; un token basura da 400 `invalid_reset_token` |
| `/forgot-password` confirma tras el envío, sea cual sea el resultado | Navegador; por el intermediario, con un email no registrado | Mismo mensaje y formulario desactivado. Revisado por el desarrollador |
| `/reset-password` lee el token, envía el formulario y redirige a `/login` | Navegador, con el enlace del correo | Vuelta a `/login?reset=success` con el aviso. Revisado por el desarrollador |
| `/reset-password` muestra un error claro y el enlace a `/forgot-password` | Navegador, con un enlace ya usado; por el intermediario, con un token basura | El error de la API y "Solicitar un nuevo enlace" (revisado por el desarrollador); 400 `invalid_reset_token` |
| `/login` tiene un enlace visible "¿Olvidaste tu contraseña?" | Navegador | Bajo el campo de la contraseña. Revisado por el desarrollador |
| `/account/change-password` comprueba la confirmación, llama a la API y muestra el resultado | Navegador; por el intermediario: contraseña actual incorrecta, nueva demasiado corta, sin token y datos válidos | Aviso si no coinciden, sin llamar a la API; 400, 422 con el campo, 401 y 200 con token nuevo ("Contraseña actualizada."). Revisado por el desarrollador |
| `change-password` responde 400 a una contraseña actual incorrecta | `test_change_password_rejects_a_wrong_current_password`; en vivo por el intermediario | 400 `invalid_current_password` |
| Ninguna API key en el código: los secretos vienen del entorno | `git grep` y `git log -p` buscando claves de Resend; `git check-ignore services/brasaland-api/.env` | Sin coincidencias en el árbol ni en el historial; `.env` está ignorado; `.env.example` deja `RESEND_API_KEY=` vacía |
| Sin regresiones | `cd services/brasaland-api && uv run pytest`; `npx tsc --noEmit`, `npm run lint` y `npm run build` en `uis/backoffice` | Pasan 433 pruebas (361 anteriores y 72 nuevas); el backoffice compila sin errores |

---

## Gestor de incidencias centralizado

Registro y seguimiento de incidencias desde el backoffice, con el histórico del analizador cargado como seed. Coinciden exactamente con el briefing:

- los campos del modelo (`id`, `title`, `description`, `category`, `status`, `origin`, `branch`, `created_at`, `updated_at`) y todos sus valores permitidos: 8 categorías, 4 estados, 3 orígenes y 15 sedes, con los nombres para mostrar del briefing;
- el ciclo de vida (`open → in_progress | discarded`, `in_progress → resolved | discarded`; `resolved` y `discarded` finales);
- las transformaciones del seed (mapas de estado, categoría y sede, `title` con los primeros 120 caracteres de `description`, `date` como medianoche UTC y `origin: "customer"`);
- los totales esperados tras el seed: 96 registros válidos; `open` 32, `resolved` 50, `discarded` 14; `customer_complaint` 48, `equipment_failure` 17, `supply_issue` 22, `staff_issue` 9;
- la estructura del monorepo: `scripts/seed_incidents.py`, `packages/shared/`, `services/brasaland-api/` y `uis/backoffice/`.

Las diferencias son de rutas, de cómo se evita duplicar el seed, del alcance del 400 y de lo que el briefing no concreta.

> **Estado:** implementado y verificado. El desarrollador revisó en el navegador el formulario y el panel, incluida la reversión del estado con la API apagada.

| Qué | Consigna o briefing | Implementación | Motivo principal |
| --- | --- | --- | --- |
| Rutas | `/api/incidents`, `/api/incidents/{id}`, `/api/incidents/summary`… | Bajo `/api/v1/incidents...`; desde el navegador, el intermediario expone exactamente `/api/incidents...` | Versión única de la API, como en todos los ejercicios anteriores |
| Control de duplicados del seed | Por `incident_id`, que "no se almacena"; si falta, `title + created_at` | `incident_id` en una tabla aparte, `incident_seed_log`, fuera del modelo | Sin guardarlo no se puede comprobar después; `title + created_at` no sirve con este CSV |
| Código de los errores de validación | 400 | 400 en las rutas del gestor; el resto de la API mantiene 422 | No cambiar el contrato de proveedores y autenticación, ya entregados |
| `status` en el formulario | "Incluye todos los campos del modelo" | Se muestra fijo en `open`, no editable; la API solo acepta `open` al crear | Una incidencia recién registrada no puede nacer resuelta o descartada |
| Menú en móvil y tablet (resuelta) | Registro "accesible desde el menú de la aplicación" | Hasta el 16 de noviembre, desde `xl` en la cabecera y por debajo en la portada; desde entonces, en el desplegable "Incidencias" y, por debajo de `xl`, en el menú hamburguesa | Antes no cabía en la cabecera de pantallas pequeñas; el menú hamburguesa lo resolvió ([apartado 5](#5-el-menú-en-móvil-y-tablet)) |
| Lógica compartida | Extraída a `packages/shared/` | Paquete Python `brasaland-shared` junto al paquete TypeScript que ya había en esa carpeta | La carpeta ya existía con `@repo/shared-types`; los dos conviven sin tocarse |

### 1. Rutas bajo `/api/v1`

Es la misma decisión que en [el analizador](#2-backend-servicesbrasaland-api-y-rutas-bajo-apiv1), los proveedores y la autenticación. Desde el navegador, las rutas se ven como en la consigna: el backoffice llama a `/api/incidents`, `/api/incidents/summary`, `/api/incidents/{id}/status`…, y su intermediario las reenvía a `/api/v1/incidents/...`. La comprobación de los totales tras el seed se hizo por esa ruta, `/api/incidents/summary`.

La carpeta del servicio ya no es una divergencia: la estructura de este ejercicio admite `services/<nombre-del-servicio-api>/`.

### 2. Cómo no duplica el seed: `incident_seed_log`

El briefing pide usar `incident_id` para la idempotencia, pero también dice que ese campo "no se almacena". Para comprobar en una segunda ejecución que una fila ya se cargó, el identificador tiene que estar guardado en algún sitio.

- **Qué se hizo:** el repositorio guarda cada `incident_id` cargado en una tabla aparte, `incident_seed_log` (`source_id` → `incident_id`). La incidencia no tiene ese campo, así que el modelo y la API son exactamente los del briefing. La comprobación y las dos inserciones se hacen con el mismo bloqueo.
- **Por qué no `title + created_at`:** el briefing lo propone para cuando falta `incident_id`. Con `incidents-brasaland.csv` no sirve como clave: tres parejas de registros válidos comparten descripción y fecha, así que el seed cargaría 93 registros y los totales no cuadrarían. Se usa solo si una fila no trae `incident_id` (en este CSV, ninguna).

### 3. 400 solo en el gestor

La consigna pide que los errores de validación devuelvan 400. El resto de la API responde 422 desde el primer ejercicio, y AUTH-01 a AUTH-03 y el directorio de proveedores ya están entregados con ese contrato (el backoffice y sus pruebas cuentan con él). Por eso:

- las rutas del gestor usan una clase de ruta propia (`BadRequestValidationRoute`) que convierte el error de validación en 400;
- el cuerpo es el mismo de siempre: `{"error": {"code": "invalid_request", "message": ..., "details": [{"field", "message"}]}}`, con el campo problemático y un mensaje en español;
- el resto de la API no cambia (una prueba lo comprueba).

Una transición no válida también responde 400 (`invalid_transition`), con un mensaje que dice a qué estados se puede pasar.

### 4. `status` fijo al registrar

El formulario "incluye todos los campos del modelo". `id`, `created_at` y `updated_at` los genera el sistema; `status` se muestra en el formulario, pero fijo en `open` con su descripción del briefing ("Incidencia recién registrada, pendiente de asignar"). Una incidencia no puede nacer `in_progress`, `resolved` o `discarded`: el ciclo de vida empieza en `open`. La API acepta `status` al crear solo si es `open` y responde 400 con cualquier otro. El histórico del seed sí entra con su estado (`resolved` o `discarded`), porque ya ocurrió.

### 5. El menú en móvil y tablet

La consigna pide que la página de registro sea "accesible desde el menú de la aplicación".

- **Hasta el 16 de noviembre de 2026:** desde 1280 px (`xl`), la cabecera mostraba un enlace por herramienta, entre ellos "Registrar incidencia" y "Gestor de incidencias". Por debajo, solo mostraba el logo y la cuenta, y se navegaba desde la portada, que tiene una tarjeta por herramienta. Los enlaces no cabían junto a la cuenta y no podían pasar a una segunda línea, porque la barra de filtros de `/talento` depende de la altura fija de la cabecera.
- **Desde entonces** (rama `feature/backoffice-navigation`): el menú agrupa las herramientas en secciones, y las tres de incidencias están en el desplegable "Incidencias". Por debajo de `xl`, un menú hamburguesa despliega las mismas secciones en un panel que se superpone a la página, sin cambiar la altura de la cabecera. El registro es accesible desde el menú en todos los tamaños, así que esta divergencia ya no existe.

### 6. Decisiones de funcionamiento

Estas decisiones no se apartan del briefing, pero concretan lo que no especifica.

| Decisión | Motivo | Límite conocido |
| --- | --- | --- |
| La lógica del CSV se movió a `packages/shared` sin cambiar ninguna regla; la API la instala como dependencia local editable (uv) y los scripts la importan por `sys.path` | La consigna lo evalúa ("sin duplicación"); cada función existe una sola vez | Los scripts deben ejecutarse dentro del repositorio |
| El seed se ejecuta con el entorno de la API: `uv run --project services/brasaland-api python scripts/seed_incidents.py` | Escribe con el repositorio de la API (TinyDB) | Necesita `uv sync` en la API |
| La API no siembra al arrancar; el seed es un paso explícito | "A partir de ahí, el formulario es la única vía de entrada" | — |
| Los inválidos se listan al final con su fila y la etiqueta de la regla del analizador (en inglés, como en su briefing) | Criterio "se reportan en consola" | Las etiquetas no se tradujeron para que coincidan con el analizador |
| Incidencias en la tabla `incidents` de `brasaland-db.json`, con un bloqueo por archivo compartido con proveedores | "Reutiliza la base de datos"; TinyDB reescribe el archivo entero en cada escritura | No protege frente a otro proceso escribiendo a la vez (el seed con la API arrancada solo evita la colisión de IDs) |
| `id` entero (el `doc_id` de TinyDB), como proveedores | "Identificador único generado automáticamente" | — |
| `title` de 1 a 120 caracteres y `description` de 1 a 2.000, sin espacios en los extremos | 120 es el recorte del seed; 2.000 basta para una descripción detallada | — |
| `GET /incidents/summary` devuelve todas las claves de cada desglose, también en 0 | "Métricas en cero" con la base vacía; el panel no tiene que adivinar qué falta | — |
| El listado se ordena de la más reciente a la más antigua | Lo primero que interesa a Operaciones | — |
| Sin campo de autor (`reported_by`) | El modelo del briefing no lo incluye | El briefing menciona "quién reportó"; con la sesión ya disponible, sería una mejora sencilla |
| Prioridad futura: `customer_complaint` abiertas más de 48 h | El briefing pide que el filtro sea fácil de implementar | Basta con `category`, `status` y `created_at` (UTC), que el modelo ya tiene |
| Cualquier excepción no controlada de la API responde 500 `internal_error` con un mensaje genérico | "Nunca el stack trace completo" | El detalle queda en el log del servidor |
| El intermediario corta a los 15 s (504 `api_timeout`) y el cliente muestra un texto comprensible ante cualquier 5xx sin mensaje propio | "Tiene que funcionar bien aunque la API tarde, aunque devuelva un 500" | Afecta a todas las herramientas del backoffice |
| Cambio de estado optimista en el listado, solo con las transiciones válidas | El briefing pide que, si falla, vuelva al valor anterior y avise | La fila se restaura completa, también `updated_at` |
| Fechas del panel en UTC, con la zona explícita | El histórico se cargó como medianoche UTC; en hora de Colombia aparecería el día anterior | Las incidencias nuevas también se ven en UTC |
| Campos y botón grandes en el formulario (`size="lg"`) | "Los campos deben ser suficientemente grandes" (tablets en cocina y sala) | — |
| Categorías, estados y orígenes se muestran con su código exacto y la descripción del briefing como apoyo; las sedes, con su nombre para mostrar | Regla de nombres exactos; el briefing pide expresamente el nombre legible de la sede | — |

### 7. Cómo verificarlo

Ejecutado el 8 de noviembre de 2026. Las pruebas en vivo usaron la API y el backoffice en local; las del seed y los totales, una base TinyDB temporal (`BRASALAND_DB_PATH`). Hay una fila por cada criterio de evaluación de la consigna.

| Criterio | Comando o acción | Resultado |
| --- | --- | --- |
| El modelo incluye todos los campos con sus restricciones | `tests/domains/incidents/test_manager_models.py` | Valores exactos del briefing, obligatorios, límites y valores no permitidos rechazados |
| El seed carga el histórico con `origin: "customer"` | `uv run --project services/brasaland-api python scripts/seed_incidents.py` sobre una base temporal | 96 insertadas; `by_origin.customer` 96 |
| El seed aplica las transformaciones del briefing | `scripts/test_seed_incidents.py` (mapas, título, fecha, sede, `central` sin mapeo) | Pasan |
| Los inválidos no se insertan y se reportan en consola | El mismo comando | 4 inválidos (`BRS-000044`, `BRS-000049`, `BRS-000079`, `BRS-000086`) con su fila y motivo; ninguno en la base |
| El seed es idempotente | Segunda ejecución | 0 insertadas y 96 omitidas; el total sigue en 96 |
| Tras el seed, `/api/incidents/summary` da los totales esperados | `GET /api/incidents/summary` por el intermediario del backoffice | `open` 32, `resolved` 50, `discarded` 14; `customer_complaint` 48, `equipment_failure` 17, `supply_issue` 22, `staff_issue` 9 |
| Códigos HTTP correctos en éxito y error | `tests/integration/test_manager_router.py` (antes en `tests/domains/incidents/`); rutas protegidas | 201, 200, 400, 404 y 401 sin token |
| Los errores de validación identifican el campo | Las mismas pruebas; en vivo, alta sin sede y con categoría inválida | 400 con `details` de `category` y `branch` |
| Ningún endpoint expone un stack trace | `test_unexpected_error_is_500_with_a_generic_message` | 500 `internal_error` con mensaje genérico, sin el detalle interno |
| Las transiciones inválidas se rechazan con 400 | Pruebas de transiciones; en vivo, `open → resolved` | 400 `invalid_transition`: "Desde open solo se puede pasar a in_progress o discarded." |
| `/summary` es correcto sin incidencias | `test_summary_is_all_zeros_with_an_empty_database` | `total` 0 y todas las claves en 0 |
| El formulario valida los obligatorios en el cliente | Navegador: enviar vacío | Cada campo marcado, sin llamar a la API. Revisado por el desarrollador |
| Con `origin = branch`, la sede se resalta y el desplegable usa las etiquetas del briefing | Navegador | Borde ámbar y aviso; "Medellín Centro", "Central (Medellín / Miami)"… Revisado por el desarrollador |
| Carga visible y botón deshabilitado durante el envío | Navegador | Indicador y "Registrando incidencia...". Revisado por el desarrollador |
| Errores de la API comprensibles, nunca técnicos | Navegador con la API apagada; en vivo, API colgada | "La API de Brasaland no está disponible…" (502) y "La API tarda demasiado en responder…" (504 a los 15 s). Revisado por el desarrollador |
| El listado gestiona cargando, vacío y con datos | Navegador | Los tres estados, más el error con "Reintentar" y "sin resultados con los filtros". Revisado por el desarrollador |
| El cambio de estado se revierte si falla | Navegador con la API apagada | La fila vuelve al estado anterior y avisa. Revisado por el desarrollador |
| El resumen no rompe la página si falla | Navegador con la API apagada | Solo ese bloque muestra el error con "Reintentar". Revisado por el desarrollador |
| La validación está en `packages/shared/` y la reutilizan script y API, sin duplicación | `git grep` de cada definición; pruebas del analizador | Cada función y constante existe una sola vez, en `packages/shared/brasaland_shared/incidents/`; 32 pruebas del script y 24 de la API sin cambios |
| El código sigue la estructura del monorepo | Árbol del repositorio | `scripts/seed_incidents.py`, `packages/shared/`, `services/brasaland-api/` y `uis/backoffice/` |
| Sin regresiones | `uv run pytest` en la API; `python -m unittest` en `scripts/incident-report`; pruebas del seed; `tsc`, `lint` y `build` en `uis/backoffice` | 539, 32 y 16 pruebas pasan; el backoffice compila sin errores |

---

## Auditoría de gestión de errores

Revisión transversal del repositorio (frontend, backend y scripts) para aplicar una estrategia de errores coherente, sin funcionalidades nuevas. Coinciden con el briefing:

- la rama `feature/error-handling-audit`;
- los ocho criterios de evaluación: tres estados en las operaciones asíncronas, mensajes legibles con llamada a la acción, capturas acotadas, `finally` para limpiar la carga, `?.` y valores por defecto, errores del backend estructurados con su código HTTP, nada sensible en la salida al cliente, y scripts que gestionan la E/S y terminan con un código distinto de cero;
- un commit por corrección, con qué se corrigió y por qué.

Las diferencias son tres puntos en que el código se aparta a propósito de la letra del checklist, cada uno con su motivo.

> **Estado:** los 29 hallazgos de la auditoría están corregidos (2026-11-09). Pruebas: 559 de la API, 36 del analizador y 20 del seed de incidencias; `tsc`, `lint` y `build` sin errores en el backoffice y la web. La prueba manual en el navegador de los estados de error queda pendiente.

| Qué | Consigna o briefing | Implementación | Motivo principal |
| --- | --- | --- | --- |
| Errores en `/funciones` | Ningún mensaje técnico en crudo | Mensaje en español y, aparte, el error técnico (`detail`) | Es una herramienta manual de pruebas para quien desarrolla; ocultar el error le quita su utilidad |
| Ruta de la base en los comandos de consola | Las respuestas de error no exponen rutas internas; quitar los `print` con información interna sensible | `uv run seed`, `uv run create-admin` y `seed_incidents.py` muestran la ruta absoluta de la base | Solo la ve quien opera el servidor, en su consola; confirma qué archivo se modificó |
| Ámbito de las capturas en `create-admin` | Capturas acotadas a operaciones específicas, no a funciones enteras | Un `try` alrededor de toda la lógica captura la cancelación y los errores de la base | La cancelación puede llegar en cualquiera de las tres preguntas y la base se usa en tres puntos |

### 1. `/funciones` muestra el error técnico

`/funciones` (página "Pruebas del Sistema (Manual)") ejecuta las funciones de `@repo/brasa-core` con datos de muestra, sin red. Esa librería no lanza errores propios, así que solo pueden llegar fallos inesperados de JavaScript, como un `TypeError`. Si se tradujeran a un mensaje genérico, como en el resto del backoffice, quien prueba las funciones perdería justo el dato que necesita.

El resultado muestra primero un mensaje en español ("La función falló de forma inesperada. Revisa el detalle técnico y los datos de entrada.") y, en un campo aparte, el nombre y el mensaje del error. El README del backoffice lo explica en sus limitaciones. La página ya está marcada como temporal: cuando esas reglas pasen al backend, se retira o llama a la API.

### 2. Ruta absoluta de la base en los comandos de consola

El checklist pide que las respuestas de error no expongan rutas internas y que se eliminen los `print` con información interna sensible. Los tres comandos que escriben en las bases TinyDB (`uv run seed`, `uv run create-admin` y `scripts/seed_incidents.py`) muestran la ruta absoluta del archivo que usan. Se mantiene por tres motivos:

- **No llega a ningún cliente.** Solo la ve quien opera el servidor, en su propia consola. La API nunca la devuelve.
- **Una ruta relativa sería ambigua.** `BRASALAND_DB_PATH` y `AUTH_DB_PATH` pueden apuntar fuera del servicio, y la ruta absoluta es la que confirma qué archivo se modificó. Durante la propia auditoría sirvió para eso: un comando lanzado con la variable equivocada mostró que había ido a la base real.
- **Ya estaba probado así.** Una prueba del seed de incidencias comprueba que se muestra la ruta resuelta.

Cada punto del código lleva un comentario con el motivo, y los README de la API (apartado "Comandos de consola") y de `scripts/` lo documentan. La búsqueda final de `console.*`, `print` y `logger` no encontró nada sensible: el intermediario del backoffice registra el método, la ruta sin query y la causa, nunca cabeceras ni cuerpo, y el correo registra solo el asunto.

### 3. Capturas de `create-admin` alrededor de toda su lógica

El resto de los scripts captura cada operación por separado (leer el CSV, abrir la base, cargar los datos). `create-admin` usa un único `try` alrededor de su lógica, que pasó a una función interna, `_create_or_promote`. Ese `try` no engulle todos los errores: solo captura cuatro tipos concretos, con un mensaje propio para cada uno:

- `KeyboardInterrupt` (código 130);
- `EOFError`;
- `json.JSONDecodeError`, una base corrupta;
- `OSError`.

Se hace así porque esos errores no pertenecen a una sola operación. Ctrl+C o el fin de la entrada pueden llegar en cualquiera de las tres preguntas (email, contraseña y repetición), y la base se lee o se escribe en tres puntos (buscar el email, promover y crear). Una captura por operación repetiría los mismos cuatro bloques en seis sitios.

Como todas las preguntas se hacen antes de escribir, cancelar nunca deja cambios a medias. Los errores de validación del email y la contraseña sí se capturan en su operación, como antes.

---

## Batería de pruebas de autenticación

Pruebas unitarias de la API de autenticación (ticket AUTH-088), en la rama `feature/auth-tests`. Coinciden con el ticket y el checklist:

- pytest para la API y Jest para la lógica TypeScript;
- un módulo de pruebas por endpoint, con camino feliz, caso límite y modo de fallo en cada uno;
- el plan de casos escrito en `TESTING.md` antes de la primera prueba;
- `uv run pytest` y `jest --coverage` pasan;
- al menos un 70 % de cobertura del módulo de autenticación (88 %);
- la revisión asistida por IA y los bugs que encontró, documentados en `TESTING.md`.

Las diferencias son de ubicación, de alcance y de herramientas. Además, la batería obligó a tocar código de producción en tres puntos.

> **Estado:** batería completa (2026-11-10). pytest: 705 pruebas pasan (146 de ellas son la batería unitaria nueva). Jest: 55 pasan. Cobertura de autenticación con solo `tests/auth/`: 88 %. Encontró dos bugs, ya corregidos (H-1 y H-2).

| Qué | Consigna o briefing | Implementación | Motivo principal |
| --- | --- | --- | --- |
| Ubicación de `TESTING.md` | En la raíz del proyecto | `services/brasaland-api/TESTING.md`, más `TESTING.es.md` | El repositorio es un monorepo: la raíz del proyecto FastAPI es el servicio. Va en dos idiomas, como sus README |
| Instalación de `pytest-cov` | `uv add --dev pytest pytest-cov httpx` | `uv add --optional dev pytest-cov` (extra `dev`); pytest y httpx ya estaban | Convención del servicio: sus dependencias de desarrollo están en el extra `dev`, que se instala con `uv sync --extra dev` |
| Pruebas HTTP existentes | Probar la lógica, no la serialización HTTP | Las 99 pruebas de router de auth se conservan en `tests/integration/`, con el marker `integration`; la batería unitaria nueva está en `tests/auth/` | Protegen el contrato con el backoffice; `-m "not integration"` las excluye |
| Qué es "la API de autenticación" | Ejemplos: registro, login y token | Los 15 endpoints de `auth`, `users` y `profiles` (AUTH-01 y AUTH-03): 16 módulos en `tests/auth/` | Es toda la API de autenticación construida en el hito anterior |
| Medida del 70 % | `uv run pytest --cov` | El 70 % se mide con solo `tests/auth/` sobre los cuatro módulos de autenticación (88 %); `uv run pytest --cov` da un 98 % de toda `app/` | Con las pruebas HTTP la cifra ya era del 98 %: no demostraría nada sobre la batería nueva |
| Código de producción | Escribir pruebas; corregir los bugs que revelen | Decisión del login extraída a `issue_login_token`; bugs H-1 y H-2 corregidos | Lo primero, para probar sin HTTP; lo segundo, porque el checklist pide corregir los bugs encontrados |
| Funciones de Jest | Generación de tokens, validación y hash de contraseñas | Validación de formularios, `safeNext`, token en `localStorage` y errores de la API (`lib/auth/`) | El backoffice no genera tokens ni calcula hashes: eso vive en la API y lo cubre pytest |
| Entorno de Jest | `npm install --save-dev jest @types/jest ts-jest` | Lo mismo, más `jest-environment-jsdom` | `token.ts` y `navigation.ts` usan `localStorage` y `window` |

### 1. `TESTING.md` en el servicio y en dos idiomas

El checklist pide `TESTING.md` "en la raíz de tu proyecto", y el ticket, "junto al código de la API existente". En este monorepo, el proyecto FastAPI es `services/brasaland-api/`: ahí están `pyproject.toml` y `tests/`, y desde ahí se ejecuta `uv run pytest`. En la raíz del repositorio conviven otros proyectos (backoffice, web, scripts) que no tienen nada que ver con esta batería.

El mismo documento recoge también las pruebas de Jest del backoffice, en su propia sección, para que el plan de AUTH-088 esté en un solo sitio. El README del backoffice enlaza a esa sección. Como los README del servicio, se publica en inglés (`TESTING.md`) y en español (`TESTING.es.md`), con el mismo contenido.

### 2. `pytest-cov` en el extra `dev`

La consigna instala las herramientas con `uv add --dev`, que las pondría en un grupo de dependencias de uv. El servicio ya declaraba pytest y httpx en `[project.optional-dependencies] dev`, y sus README indican `uv sync --extra dev`. Si `pytest-cov` fuera a otro sitio, habría dos listas de herramientas de desarrollo y una instalación no traería la otra. Por eso se añadió con `uv add --optional dev pytest-cov`, y la configuración de cobertura (`[tool.coverage]`) está en `pyproject.toml`.

### 3. Las pruebas HTTP se conservan como integración

Antes de AUTH-088 había unas 99 pruebas de router de autenticación con `TestClient` (214 casos con la parametrización). Comprueban cosas que la consigna excluye de la batería unitaria: códigos de estado, el formato `{"error": {...}}`, cabeceras como `WWW-Authenticate` y el montaje de las rutas protegidas.

No se borraron ni se convirtieron, porque son el contrato con el backoffice: una prueba unitaria no detecta, por ejemplo, que una ruta nueva quedó sin protección. Se movieron a `tests/integration/` con el marker `integration`:

- `uv run pytest` las ejecuta junto con todo lo demás;
- `uv run pytest -m "not integration"` las excluye;
- la batería que pide el ticket es `tests/auth/`, y las mide aparte (punto 5).

### 4. La API de autenticación son 15 endpoints

La consigna pone como ejemplos `test_register.py`, `test_login.py` y `test_token.py`. La API de autenticación del hito anterior (AUTH-01, ampliada en AUTH-03) tiene 15 endpoints en tres dominios:

- `auth`: login, `me`, `forgot-password`, `reset-password/validate`, `reset-password` y `change-password`;
- `users`: registro, listar, leer, editar y borrar;
- `profiles`: leer y editar el propio perfil y el de otra cuenta.

Todos deciden algo sobre credenciales o permisos, así que entran en la batería: un módulo por endpoint más `test_token.py`, 16 en total. Los nombres de la consigna se respetan donde coinciden (`test_register.py`, `test_login.py` y `test_token.py`).

### 5. Cómo se mide el 70 %

Con la batería completa, la cobertura de autenticación ya era del 98 % antes de AUTH-088, gracias a las pruebas HTTP. Dar esa cifra no diría nada de la batería nueva. Por eso el objetivo del 70 % se mide con solo `tests/auth/` sobre `core/security.py` y los dominios `auth`, `users` y `profiles`:

```bash
uv run pytest tests/auth --cov=app.core.security --cov=app.domains.auth \
  --cov=app.domains.users --cov=app.domains.profiles
```

El resultado es un 88 %. `uv run pytest --cov` sigue funcionando sin argumentos, como pide la consigna, y da un 98 % de toda `app/`. `TESTING.md` explica qué queda sin cubrir y por qué: sobre todo el comando de consola `create-admin` y la lectura HTTP del cuerpo del login.

### 6. Cambios en el código de producción

El ticket es de pruebas, pero se cambió código de producción en tres puntos, cada uno en su propio commit:

- **Decisión del login (`issue_login_token`).** La ruta `POST /auth/login` recibe la petición cruda para aceptar JSON y formulario, así que no se podía llamar sin construir un `Request`. Su decisión (401 `invalid_credentials`, 403 `inactive_user` o token) pasó a una función propia que la ruta llama. El comportamiento no cambia.
- **Bug H-1.** Cambiar la contraseña por `PUT /users/{id}` no cerraba las sesiones anteriores ni anulaba los enlaces de restablecimiento. Ahora lo hace, como `change-password`. **Cambia el comportamiento:** quien cambie su propia contraseña por esa ruta tiene que volver a iniciar sesión, porque la respuesta no trae un token nuevo. El backoffice no usa esa ruta para la contraseña.
- **Bug H-2.** `change-password` respondía 400 «La contraseña actual no es correcta» si la cuenta se borraba durante el cambio. Ahora responde 401 `invalid_token`, como cualquier petición con el token de una cuenta borrada.

Los dos bugs salieron de la revisión asistida por IA y se confirmaron con pruebas. El checklist pide corregirlos y documentarlos: están en "Bugs encontrados" de `TESTING.md`, con su prueba de regresión.

### 7. Jest prueba las utilidades de autenticación que tiene el backoffice

El checklist sugiere probar la generación de tokens, la validación y los helpers de hash. El backoffice no genera tokens ni calcula hashes: los recibe de la API, que es donde los prueba pytest (`test_token.py` y `test_register.py`). Sus utilidades de autenticación, que son las que se prueban, son:

- la validación de los formularios (`lib/auth/validation.ts`), con los mismos límites que la API;
- `safeNext` y `loginUrl` (`lib/auth/navigation.ts`), que impiden las redirecciones abiertas tras el login;
- el token en `localStorage` (`lib/auth/token.ts`), incluido el almacenamiento bloqueado;
- el reparto de los errores de la API por campo (`lib/auth/api-errors.ts`) y `errorFromStatus`.

La configuración es `jest.config.js` (la consigna admite `.ts` o `.js`; `.ts` exigiría `ts-node`). Se añadió `jest-environment-jsdom` porque `token.ts` y `navigation.ts` necesitan `window` y `localStorage`; las demás pruebas se ejecutan en `node`. `jest --coverage` se ejecuta con `npm run test:coverage` (o `npx jest --coverage`) desde `uis/backoffice/`.

### 8. Cómo verificarlo

Ejecutado el 10 de noviembre de 2026. Hay una fila por cada criterio de evaluación de la consigna.

| Criterio | Comando o acción | Resultado |
| --- | --- | --- |
| `TESTING.md` documenta el plan, cómo ejecutar y la cobertura | `services/brasaland-api/TESTING.md` (y `.es.md`) | Plan por endpoint escrito antes de las pruebas (commit `e5ef1f5`), comandos de cada suite, cobertura y bugs encontrados |
| `uv run pytest` pasa sin errores | `uv run pytest` en `services/brasaland-api/` | 705 pasan, 0 fallan (unos 2 min) |
| Camino feliz, caso límite y modo de fallo en cada endpoint | `tests/auth/`, un módulo por endpoint | Los 15 endpoints y los tokens tienen casos F, L y X; los IDs de las pruebas coinciden con las tablas de `TESTING.md` |
| Cobertura de autenticación ≥ 70 % | `uv run pytest tests/auth --cov=...` (punto 5) | 88 % (con toda la batería, 98 %) |
| Lógica de negocio, no serialización HTTP | Revisión de `tests/auth/` | Ninguna usa `TestClient`: llaman a las funciones de ruta y a los servicios, y afirman el `ApiError` o lo guardado |
| Jest presente y pasando | `npm run test:coverage` en `uis/backoffice/` | 55 pasan; `lib/auth/` al 96 %. `tsc`, `lint` y `build` pasan |
| Flujo asistido por IA evidente | "Revisión asistida por IA" y "Bugs encontrados" de `TESTING.md` | 7 casos marcados (IA) y dos bugs confirmados y corregidos (H-1 y H-2) |
| Código limpio y nombres claros | Revisión | Nombres con el ID del caso (`test_tok_l1_…`), estructura F/L/X en cada módulo, fixtures y helpers comunes, comentarios en las afirmaciones no evidentes |

### 9. Extra API-042: proveedores y gestor de incidencias

Ticket extra de la misma consigna, en la misma rama. Coinciden con el ticket: dos grupos de endpoints del backoffice distintos de la autenticación (el directorio de proveedores y el gestor de incidencias), los tres niveles en cada endpoint, módulos nuevos en `tests/` y `TESTING.md` con los resultados de cobertura. Las decisiones E-1 a E-5 están en la sección "API-042" de `TESTING.md`.

| Qué | Ticket | Implementación | Motivo |
| --- | --- | --- | --- |
| Pruebas de router existentes | No dice nada | `test_supplier_router.py`, `test_manager_router.py` y `test_router.py` (renombrado a `test_incident_analyzer_router.py`) pasan a `tests/integration/` | Mismo criterio que en AUTH-088: las pruebas HTTP son integración y `-m "not integration"` las excluye todas |
| Medida del 60 % | "En los módulos que pruebes" | Solo `tests/suppliers/` y `tests/incidents/`, sobre los dos dominios completos: 84 % | Con las pruebas que ya existían la cifra era del 98 %; incluye el analizador del CSV, que no se probó y aun así se mide |

Verificación (10 de noviembre de 2026): `uv run pytest tests/suppliers tests/incidents` da 101 pruebas que pasan; con `--cov=app.domains.suppliers --cov=app.domains.incidents`, 84 %. La batería completa (`uv run pytest`) da 806 pruebas que pasan.

### 10. Extra FE-019: utilidades del frontend

Ticket extra de la misma consigna, en la misma rama. Coinciden con el ticket: tres utilidades del frontend Next.js (`lib/format.ts`, `toUserMessage` y `readJson`), con un caso feliz y uno de fallo por función, en un directorio `__tests__/` del proyecto frontend (`uis/backoffice/__tests__/utils/`).

| Qué | Ticket | Implementación | Motivo |
| --- | --- | --- | --- |
| Instrucciones de ejecución independiente | En `TESTING.md` | En `services/brasaland-api/TESTING.md` (sección "FE-019") y en el README del backoffice: `npm test -- __tests__/utils` | El `TESTING.md` de AUTH-088 está en el servicio (apartado 1); el README del frontend enlaza a él |
| Zona horaria de las pruebas | No dice nada | `jest.config.js` fija `TZ=UTC` | `lib/format.ts` formatea en la hora local: sin esto, las fechas esperadas dependerían del equipo |

Verificación (10 de noviembre de 2026): `npm test -- __tests__/utils` da 35 pruebas que pasan; `npm run test:coverage` da 90 que pasan, con `lib/format.ts` y `lib/error-message.ts` al 100 % y `readJson` cubierta por completo. `tsc --noEmit` y `npm run lint` pasan.

---

## Gestión de inventario con ORM

Inventario de ingredientes con stock calculado (Hito 5, ticket BRD-0512), en la rama `feature/inventory-orm`. La API mantiene dos conexiones a la vez: TinyDB para la autenticación y Supabase (PostgreSQL, con SQLModel) para el inventario. Coinciden exactamente con el briefing:

- las entidades `Ingredient`, `IngredientEntry` e `IngredientExit` y todos sus campos;
- los valores válidos de `unit`, `category`, `country` y `reason`, y `location_id` de 1 a 14;
- `current_stock` calculado como `SUMA(entradas) − SUMA(salidas)`, solo en el schema de respuesta y nunca como columna;
- la FK de las órdenes a `Ingredient`, aplicada por la base de datos, y `user_uuid` sin FK ni tabla de usuarios en Supabase;
- el 400 de una salida que dejaría el stock en negativo, antes de escribir nada;
- los 6 endpoints del briefing, con un `APIRouter(prefix="/inventory")`;
- los datos semilla: los 6 ingredientes, 4 entradas (2 de `BRS-BEEF-001`) y 3 salidas, una de ellas `"waste"`.

Las diferencias son de ubicación, rutas, idioma y lo que el briefing no concreta. Las decisiones D1 a D7 se tomaron con el desarrollador el 14 de noviembre de 2026.

> **Estado:** implementado y verificado en vivo contra Supabase (2026-11-14). `uv run pytest`: 916 pruebas pasan (110 de inventario y de la conexión SQL); cobertura del dominio, 97 %.

| Qué | Consigna o briefing | Implementación | Motivo principal |
| --- | --- | --- | --- |
| Estructura de archivos (D1) | `services/main.py`, `database.py`, `models.py`, `schemas.py` y `routers/inventory.py` | Dominio `app/domains/inventory/` (`models.py`, `schemas.py`, `service.py`, `router.py`, `seed.py`) y conexión SQL en `app/core/database.py` | La consigna pide extender el servicio existente, no crear otro |
| `database.py` con las dos conexiones | "Cliente TinyDB + motor SQLModel + `get_db`" en un archivo | `app/core/database.py` solo tiene el motor SQLModel y `get_db`; TinyDB sigue en `app/core/storage.py` y `app/domains/users/database.py` | La consigna pide dejar intacta la configuración TinyDB de auth ("o equivalente") |
| Prefijo de las rutas (D2) | `/inventory/...` | `APIRouter(prefix="/inventory")` montado en `/api/v1`: `/api/v1/inventory/...` | Versión única de la API, como en todos los ejercicios anteriores |
| Origen de `user_uuid` (D3) | Un campo de la orden | Sale siempre del token (`get_current_user`); enviarlo en el cuerpo da 422 | Cada orden debe ser trazable a quien la creó; nadie puede registrarla en nombre de otro |
| Autenticación en los `GET` | La define el briefing, que no dice nada | Las 6 rutas exigen token | Como el resto de la API; el stock es un dato interno de Operaciones |
| Base de la semilla (D4) | "Tu base de datos de desarrollo local" | El proyecto de Supabase | La consigna lleva los datos de negocio a Supabase, con la cadena en `.env` |
| SQLAlchemy (D5) | "No uses SQLAlchemy directamente" | La API solo usa `sqlmodel`; el tipo `Engine` se importa bajo `TYPE_CHECKING` y las pruebas usan `sqlalchemy.event` | SQLModel no reexporta el tipo del motor ni los eventos |
| Mensaje del 400 (D6) | `"Insufficient stock for ingredient '{name}'. Available: {available}, requested: {requested}."` | `{"error": {"code": "insufficient_stock", "message": "Stock insuficiente para el ingrediente '{name}'. Disponible: {available}, solicitado: {requested}."}}` | Formato único de errores y mensajes en español de la API (decisión del desarrollador) |
| Alcance del stock (D7) | Fórmula global; `location_id` en las órdenes | Stock global por ingrediente; `GET /products?country=CO` o `US` | Es la fórmula del briefing y lo que comprueba el evaluador; `country` cubre la regla 3 |
| Forma de `GET /orders` | "Lista todas las entradas y salidas con datos del ingrediente" | `{"inbound": [...], "outbound": [...]}`, de la más reciente a la más antigua | Cada lista con su schema y sus campos propios |
| Comando de la semilla | No dice cómo | `uv run --env-file .env seed-inventory` | Como `uv run seed` y `uv run create-admin` |

### 1. Estructura de archivos y `database.py`

El hito "extiende el servicio FastAPI de tu monorepo; no crearás un nuevo servicio". La API ya organiza cada responsabilidad en un dominio, así que el inventario es uno más: `models.py` (SQLModel) y `schemas.py` (Pydantic) siguen separados, como pide la consigna, y la lógica vive en `service.py` para que el router solo traduzca HTTP.

La consigna también pide "deja intacta la configuración TinyDB de auth". Por eso el motor SQLModel tiene su propio módulo, `app/core/database.py`, y no se mezcla con el cliente TinyDB. El docstring del módulo explica qué va a cada almacén. Las dos conexiones se inicializan en el mismo arranque: la API no arranca sin `DATABASE_URL` (igual que sin `SECRET_KEY`), y `create_all` crea en Supabase las tablas que falten.

### 2. Rutas bajo `/api/v1`

Es la misma decisión que en [el analizador](#2-backend-servicesbrasaland-api-y-rutas-bajo-apiv1), los proveedores, la autenticación y el gestor de incidencias. El router tiene exactamente `prefix="/inventory"`; `main.py` lo registra bajo `API_PREFIX`. Una prueba de integración recorre el esquema OpenAPI y comprueba que las rutas de inventario son exactamente las 6 del briefing.

### 3. `user_uuid` del token y `GET` protegidos

La consigna dice que "el UUID del usuario autenticado (de TinyDB) debe almacenarse en `user_uuid`". Si el cliente pudiera enviarlo, una orden podría atribuirse a otro usuario. Por eso los schemas de entrada no admiten `user_uuid` (422) y las rutas de órdenes lo toman de `get_current_user`. La respuesta sí lo incluye.

El briefing no dice si los `GET` son públicos. Se protegen como el resto de la API: el stock y las órdenes son datos internos de Operaciones, y el backoffice ya envía el token.

### 4. Supabase como base de desarrollo

El briefing pide crear la semilla "al configurar tu base de datos de desarrollo local", pero la consigna lleva el inventario a Supabase y pide su cadena de conexión en `.env`. No hay un PostgreSQL local aparte: el proyecto de Supabase es la base de desarrollo y de la demo. Las pruebas no tocan Supabase: usan un SQLite temporal con las claves foráneas activadas.

Se usa la cadena del **Session pooler** de Supabase, que funciona por IPv4; la conexión directa del plan gratuito solo funciona por IPv6.

### 5. SQLModel sin SQLAlchemy directo

La consigna pide SQLModel y "no uses SQLAlchemy directamente", y a la vez evitar el problema N+1. La forma habitual de lo segundo (`selectinload` o `joinedload`) se importa de `sqlalchemy.orm`, así que se resolvió con lo que exporta `sqlmodel`:

- `GET /inventory/products` es una sola consulta: los ingredientes con `LEFT OUTER JOIN` a dos subconsultas que suman entradas y salidas por ingrediente (`func.sum`, `func.coalesce`).
- `GET /inventory/orders` son dos consultas, una por tabla, cada una con `select(Orden, Ingredient).join(Ingredient)`.
- Los `Relationship` están declarados, pero el código no los recorre en bucles.

Una prueba cuenta las sentencias SQL: 1 y 2 consultas, con 1 o con 20 ingredientes. Contra una versión ingenua que lee `entry.ingredient` en un bucle, el mismo contador da 21 consultas.

Hay tres usos de SQLAlchemy fuera de lo anterior, ninguno para modelar ni consultar:

- `app/core/database.py` importa el tipo `Engine` bajo `TYPE_CHECKING`, solo para las anotaciones; no se ejecuta nunca.
- SQLAlchemy 2.1 usa por defecto el driver psycopg (v3) para `postgresql://`, pero la consigna instala `psycopg2-binary`. `load_database_url` convierte la cadena de Supabase en `postgresql+psycopg2://`. Sin esto, la primera conexión real fallaba (corrección `2980037`).
- Las pruebas usan `sqlalchemy.event` para activar las claves foráneas de SQLite y para contar las consultas, e `inspect` para comprobar las tablas.

### 6. Mensaje del 400 en español

El briefing da el texto exacto en inglés. La API devuelve todos los errores con el mismo formato, `{"error": {"code", "message"}}`, y con mensajes en español desde la auditoría de errores. El desarrollador decidió traducirlo y mantener el formato: el código HTTP (400) y la información (nombre, disponible y solicitado) son los del briefing, y el código `insufficient_stock` permite detectarlo sin leer el texto. Las cantidades se muestran sin ceros sobrantes (`52`, `40.5`).

### 7. Stock global y filtro por país

La consigna pide acotar el stock "por cualquier clave de partición que defina tu BRIEFING". El briefing define la fórmula por ingrediente, sin partición, y guarda `location_id` sin hacerlo FK. El desarrollador eligió el stock global: la salida se compara con el stock total del ingrediente. La regla 3 ("usa `country` para filtrar por mercado") se cubre con `GET /inventory/products?country=CO` (o `US`).

### 8. Decisiones de funcionamiento

Estas decisiones no se apartan del briefing, pero concretan lo que no especifica.

| Decisión | Motivo | Límite conocido |
| --- | --- | --- |
| Tablas `ingredients`, `ingredient_entries` e `ingredient_exits` | Nombres en plural y en snake_case; las clases conservan los nombres del briefing | — |
| `sku` único a nivel de base de datos; 409 `duplicate_sku` | "Código interno único" | — |
| Las salidas bloquean la fila del ingrediente (`SELECT ... FOR UPDATE`) antes de calcular el stock | Dos salidas simultáneas no pueden gastar el mismo stock | SQLite (pruebas) lo ignora; se aplica en PostgreSQL |
| El stock se compara y se devuelve redondeado a 6 decimales | `0.1 + 0.2 − 0.3` debe dar 0, no un residuo de coma flotante | — |
| `unit` restringida a `kg`, `litro` y `unidad` | Son los valores que lista el briefing | Una unidad nueva exige cambiar el schema |
| `quantity` estrictamente mayor que 0, sin textos ni infinitos | Una orden de cantidad 0 o negativa no tiene sentido | — |
| `created_at` en UTC con zona (`timestamp with time zone`) | SQLModel 0.0.50 rechaza fechas sin zona | En la semilla, todas las órdenes comparten hora (una inserción por lotes); el orden desempata por `id` |
| `location_id` de la semilla: 1 para Colombia y 10 para EE. UU. | El briefing no asigna locales a países | Valores de ejemplo dentro del rango 1–14 |
| La semilla usa el UUID del administrador activo más antiguo de TinyDB | "Usa valores de `user_uuid` que correspondan a usuarios existentes" | Sin administrador, termina con código 1 y pide `uv run create-admin` |
| La semilla es idempotente y va en una única transacción | Repetirla no duplica ni deja cargas a medias | Solo siembra si no hay ingredientes |
| La API no siembra al arrancar | Necesita un usuario real de TinyDB | — |
| Sin rutas para editar o borrar ingredientes y órdenes | "Ningún endpoint permite modificar directamente un campo de stock" | Corregir un error exige una orden compensatoria |

### 9. Cómo verificarlo

Ejecutado el 14 de noviembre de 2026. La verificación en vivo usó la API en local contra el proyecto de Supabase, con un token del administrador generado por la propia API. Hay una fila por cada criterio de evaluación de la consigna.

| Criterio | Comando o acción | Resultado |
| --- | --- | --- |
| Dos conexiones presentes y usadas correctamente | Arranque de la API; `tests/core/test_database.py` | TinyDB para usuarios (`get_current_user`) y Supabase para inventario; sin `DATABASE_URL` la API no arranca |
| Endpoints agrupados bajo `/inventory` con un `APIRouter` dedicado | `test_router_exposes_exactly_the_six_briefing_routes_and_none_to_edit_stock` | Exactamente las 6 rutas del briefing bajo `/api/v1/inventory` |
| FK declaradas a la entidad del briefing | Inspección de las tablas en Supabase; `test_database_rejects_order_of_missing_ingredient` | `ingredient_entries` e `ingredient_exits` con FK a `ingredients(id)`; la base rechaza un `ingredient_id` inexistente |
| `current_stock` se calcula; ningún endpoint lo modifica | En vivo: `PATCH` y `PUT /products/1`; `current_stock` en el alta | 405; `current_stock` en el cuerpo da 422; `ingredients` no tiene columna de stock |
| El cálculo respeta el alcance del briefing | `test_stock_is_global_across_locations` | Stock global por ingrediente (D7) |
| Salida que supera el stock: 400 antes de escribir | En vivo: salida de 60 kg de Falda de ternera | 400 `insufficient_stock` con el mensaje; el stock sigue en 52 y no hay orden nueva |
| Cada orden guarda el `user_uuid` del creador autenticado | `test_each_order_stores_the_uuid_of_the_user_who_sent_it`; en vivo, `GET /orders` | El `id` de TinyDB del usuario de cada token; enviarlo en el cuerpo da 422 |
| `models.py` y `schemas.py` separados; ningún endpoint devuelve un objeto SQLModel | `test_orm_models_are_not_response_schemas`; `test_orders_list_has_ingredient_data_and_only_schema_fields` | Los schemas no heredan de SQLModel; las respuestas solo tienen los campos del schema |
| Sesión por petición con `Depends()`, sin sesión global | `test_get_db_yields_a_new_session_per_call_and_closes_it` | Una sesión nueva por llamada, cerrada al terminar |
| Parámetros de conexión en `.env`, ignorado en Git | `.gitignore` raíz (`.env*`); `.env.example` | `DATABASE_URL` solo en `.env`; la plantilla la deja vacía |
| Nombres de entidades y campos del briefing | `tests/inventory/test_models.py` y `test_schemas.py` | Columnas y valores válidos exactos |
| Semilla presente; `GET /products` refleja el neto | En vivo: `uv run --env-file .env seed-inventory` dos veces y `GET /products` | 6 ingredientes, 4 entradas y 3 salidas; la segunda vez no inserta nada. Stock: Falda 52, Costilla 32, Chimichurri 20 y el resto 0 |
| Sin N+1 | `tests/inventory/test_queries.py` | 1 consulta en `GET /products` y 2 en `GET /orders`, con 1 o con 20 ingredientes |
| Sin regresiones | `uv run pytest` | 916 pasan |

---

## Inventario en el backoffice

Sección de inventario de `uis/backoffice` (Hito 5, fase frontend, ticket BRD-0512), en la rama `feature/inventory-frontend`. Sustituye al cliente REST: el personal de Operaciones consulta el stock y registra entradas y salidas desde el backoffice, con la API de [Gestión de inventario con ORM](#gestión-de-inventario-con-orm). Coinciden con la consigna y el briefing:

- las cuatro vistas: ingredientes con su stock, registro de entradas, registro de salidas e historial de órdenes, todas protegidas;
- un módulo de integración dedicado (`lib/inventory.ts`) sin `fetch` en los componentes y con `Authorization: Bearer <token>` en cada petición;
- las entidades, campos y valores del briefing (`Ingredient`, `IngredientEntry`, `IngredientExit`; `consumption`, `waste`, `CO`, `US`, las categorías y las unidades), con su código exacto;
- la regla del stock: el cliente solo avisa; la API decide y su 400 se muestra junto a la cantidad.

Las diferencias son de configuración, rutas y una etiqueta. Las decisiones F1 a F6 se tomaron con el desarrollador el 14 de noviembre de 2026.

> **Estado:** implementado y verificado en vivo contra una API temporal (SQLite y TinyDB fuera del repositorio), sin tocar Supabase (2026-11-16). `npm test`: 159 pruebas pasan (69 de inventario); `tsc`, `lint` y `build` sin errores. El desarrollador revisó cada vista en el navegador.

| Qué | Consigna o briefing | Implementación | Motivo principal |
| --- | --- | --- | --- |
| URL de la API (F1) | `NEXT_PUBLIC_INVENTORY_API_URL=http://localhost:8000` en `.env.local` | Sin variable nueva: `lib/inventory.ts` llama a `/api/inventory/...` y el intermediario la reenvía con `API_BASE_URL` | Mismo camino que el resto de herramientas; sin CORS; la URL de la consigna no incluye `/api/v1` |
| Rutas (F2) | `/backoffice/inventory/products`, `.../orders/inbound`, `.../orders/outbound` y `.../orders` | `/inventario/ingredientes`, `/inventario/ordenes/entrada`, `/inventario/ordenes/salida` y `/inventario/ordenes`; `/inventario` redirige a ingredientes | Rutas en español, como el resto del backoffice, con el vocabulario del briefing; el backoffice es la raíz de su aplicación |
| Etiqueta de `user_uuid` | La consigna nombra el campo `user_uuid` | La columna se rotula "Usuario"; el valor es el `user_uuid` completo y la página explica qué es | Que la columna se vea como las demás (decisión del desarrollador, 16 de noviembre) |
| Menú en móvil y tablet | — | "Inventario" en la cabecera desde `xl`; por debajo, en el menú hamburguesa (desde el 16 de noviembre; antes, en la portada) | La regla del [gestor de incidencias](#5-el-menú-en-móvil-y-tablet) |

### 1. Intermediario en lugar de `NEXT_PUBLIC_INVENTORY_API_URL`

La consigna pide añadir `NEXT_PUBLIC_INVENTORY_API_URL=http://localhost:8000` a `.env.local` y llamar a la API desde el navegador. El backoffice ya tiene un intermediario (`app/api/[...path]/route.ts`) que reenvía `/api/...` a la API con `API_BASE_URL`, una variable solo de servidor. Usarlo:

- mantiene un único camino a la API para todas las herramientas, con el mismo manejo de errores (502 si la API no responde, 504 a los 15 s);
- evita configurar CORS en la API;
- evita un error de la consigna: su URL no incluye `/api/v1`, así que las llamadas darían 404.

`lib/inventory.ts` centraliza las 5 llamadas que usa el backoffice (todas las rutas menos `POST /inventory/products`, que la consigna no pide) con `apiJson`, que añade el token de la sesión, convierte cualquier `4xx` o `5xx` en un mensaje legible y cierra la sesión ante un 401. No hace falta tocar `.env.local`.

### 2. Rutas en español

| Consigna | Backoffice |
| --- | --- |
| `/backoffice/inventory/products` | `/inventario/ingredientes` |
| `/backoffice/inventory/orders/inbound` | `/inventario/ordenes/entrada` |
| `/backoffice/inventory/orders/outbound` | `/inventario/ordenes/salida` |
| `/backoffice/inventory/orders` | `/inventario/ordenes` |

El resto del backoffice usa rutas en español (`/proveedores`, `/gestor-incidencias`…), y la consigna pide el vocabulario del briefing, que habla de ingredientes, no de productos. El prefijo `/backoffice` no existe: el backoffice es la raíz de su propia aplicación. Las llamadas a la API no cambian.

### 3. La columna "Usuario"

La decisión F3 mostraba `user_uuid` con su nombre literal, como lo escribe la consigna. Al revisar el historial, el desarrollador pidió rotularla "Usuario" para que la cabecera se vea como el resto (en mayúsculas en escritorio). El contenido no cambia: es el `user_uuid` completo, en letra monoespaciada, con la etiqueta "Tú" en las órdenes propias (F6), y la descripción de la página nombra el campo `user_uuid`.

### 4. Decisiones de funcionamiento

Estas decisiones no se apartan de la consigna, pero concretan lo que no especifica.

| Decisión | Motivo | Límite conocido |
| --- | --- | --- |
| Tres niveles de stock con umbral por unidad (F4): sin stock (0, rojo), bajo (ámbar) y saludable (verde); `kg` < 40, `litro` < 25 y `unidad` < 100, en `lib/inventory-stock-level.ts` | La consigna pide umbrales propios documentados en un comentario; las cantidades de unidades distintas no son comparables | Valores iniciales: Operaciones puede ajustarlos en ese archivo, y la leyenda de la página cambia sola |
| Cada nivel lleva texto y un punto, además del color | El color no puede ser la única señal | — |
| Locales "Local 1" a "Local 14", obligatorios y sin valor por defecto (F5), desde una única lista | El briefing no da nombres a los números | Para mostrar los nombres reales basta con cambiar esa lista |
| Valores con su código exacto y la descripción del briefing cuando existe: `consumption (consumo)`, `waste (merma)`, `CO (Colombia)`, `US (Estados Unidos)` (F3) | Regla de nombres exactos, como en el gestor de incidencias | Categorías y unidades tal cual: el briefing no las describe |
| El selector de ingrediente muestra nombre, SKU y unidad | "Nunca un ID en bruto"; el SKU distingue los ingredientes de cada país | — |
| Las filas de ingredientes abren los formularios con `?ingredient_id=` preseleccionado | La consigna pide crear una orden "de ese producto" desde su fila | Un id que no existe se marca en el selector y no se envía |
| El stock de la salida se pide a la API al elegir el ingrediente (`GET /products/{id}`) y se descartan las respuestas atrasadas | "De forma reactiva, antes de introducir la cantidad" | Se refresca tras cada envío, no en tiempo real |
| La advertencia de cantidad excesiva no bloquea el envío | Es una ayuda de UX: el stock puede haber cambiado y la regla real la aplica la API | — |
| El 400 `insufficient_stock` se coloca en el campo de cantidad (`exitErrorsFromApi`) y el aviso general remite a él | "Inline, junto al campo de cantidad" | — |
| El proveedor de la entrada se elige de una lista: los proveedores activos del directorio con el país y la categoría equivalente del ingrediente (`lib/inventory-suppliers.ts`: `meat`→`carne`, `produce`→`verduras_y_hortalizas`, `sauce`→`salsas_y_condimentos`, `beverage`→`bebidas`, `packaging`→`packaging`, `cleaning`→`productos_limpieza`; `CO`→`Colombia`, `US`→`USA`). Se sigue enviando `supplier_name` con su nombre. Sin proveedores activos, un aviso enlaza al directorio y no hay texto libre (decisión del desarrollador, 16 de noviembre) | Evita nombres escritos de varias formas y deja el historial agrupable por proveedor, sin cambiar el contrato del briefing (`supplier_name` es texto) | El vínculo solo existe en la interfaz: la API acepta cualquier nombre, y no puede haber clave foránea porque los proveedores están en TinyDB y el inventario en Supabase. Si se renombra un proveedor, las entradas antiguas conservan el nombre anterior. Si cambian las categorías de alguno de los dos briefings, hay que actualizar la tabla de equivalencias |
| Pestañas del inventario en dos líneas de dos en móvil y en una línea desde `sm` | En una sola fila desplazable, "Historial de órdenes" quedaba fuera de la vista | — |
| Tras una entrada se limpia el formulario (conserva el ingrediente del enlace); tras una salida solo se limpia la cantidad y se refresca el stock | Registrar varias salidas seguidas del mismo ingrediente es lo habitual | — |
| El historial junta entradas y salidas de la más reciente a la más antigua, con "+ Entrada" en verde y "− Salida" en rojo | La API las devuelve en dos listas; la consigna pide distinguirlas | Sin filtros ni paginación |
| `user_uuid` completo con "Tú" en las órdenes propias, sin nombres ni emails (F6) | La API no los da y un usuario normal no puede leer los datos de otros | Las órdenes de otros solo muestran el UUID |
| Tarjetas en móvil y tablet; tabla desde `lg` (1024 px) | Siete columnas no caben en una tablet | — |

### 5. Cómo verificarlo

Ejecutado el 16 de noviembre de 2026, con el backoffice (`next dev`) contra una API temporal: SQLite para el inventario, TinyDB temporal para los usuarios, un administrador de pruebas y la semilla del inventario. Supabase no se tocó. Hay una fila por cada criterio de evaluación de la consigna.

| Criterio | Comando o acción | Resultado |
| --- | --- | --- |
| 1. Módulo de integración dedicado, sin `fetch` en los componentes | `lib/inventory.ts`; búsqueda de `fetch` en `components/` y `hooks/` del inventario | Las 5 llamadas pasan por `apiJson`; ningún componente usa `fetch` |
| 2. Todas las peticiones protegidas llevan `Authorization` | `__tests__/inventory/api.test.ts`; en vivo, sin token | `Bearer` con el token de `localStorage` en las 5 llamadas; 401 sin token |
| 3. La página de ingredientes carga datos reales con indicadores de nivel | En vivo, `/inventario/ingredientes` | 6 ingredientes de la semilla: Falda 52 kg saludable, Costilla 32 kg y Chimichurri 20 litros bajos, el resto sin stock. Revisado por el desarrollador |
| 4. La entrada muestra confirmación o error legible | En vivo: entrada válida, cantidad 0 con proveedor vacío e ingrediente 999 | 201 "Entrada #5 registrada: 12.5 kg de Costilla de cerdo."; 422 junto a `quantity` y `supplier_name`; 404 en el aviso. Revisado por el desarrollador |
| 5. La salida muestra el stock del ingrediente elegido de forma reactiva | Navegador | "Stock actual: 52 kg" con su nivel al elegir; cambia al cambiar de ingrediente. Revisado por el desarrollador |
| 6. La salida advierte si la cantidad supera el stock | Navegador: 3 kg de Yuca (stock 0) | Aviso ámbar junto a la cantidad, sin bloquear el envío. Revisado por el desarrollador |
| 7. El 400 de la salida se muestra en la interfaz | En vivo y en el navegador: la misma salida; `exitErrorsFromApi` en `validation.test.ts` | 400 `insufficient_stock`: "Stock insuficiente para el ingrediente 'Yuca'. Disponible: 0, solicitado: 3.", junto a la cantidad. Revisado por el desarrollador |
| 8. El historial muestra todas las órdenes con tipo, ingrediente, cantidad, fecha y `user_uuid` | En vivo, `/inventario/ordenes`; `mergeOrders` en `orders.test.ts` | Entradas y salidas juntas por fecha, con "+ Entrada"/"− Salida" y el `user_uuid` con "Tú". Revisado por el desarrollador |
| 9. Las cuatro páginas redirigen al login sin sesión | Navegador sin sesión (ventana privada) en las cuatro rutas | Las cuatro llevan a `/login?next=<ruta>`: viven en `app/(protegido)/`, cuyo `SessionProvider` protege toda página del grupo. Revisado por el desarrollador |
| 10. Entidades y etiquetas del briefing | Revisión de las vistas; `lib/inventory-labels.ts` | Ingrediente, Entrada, Salida y Órdenes; códigos exactos con su descripción. Única excepción: la columna "Usuario" ([apartado 3](#3-la-columna-usuario)) |
| Sin regresiones | `npm test`, `npx tsc --noEmit`, `npm run lint` y `npm run build` en `uis/backoffice` | 159 pruebas pasan; el build genera las 4 rutas de inventario sin errores |

---

## Contenedorización del monorepo

Entorno de desarrollo en Docker (ticket #infra-40), en la rama `feature/dockerize`. `docker compose up` desde la raíz levanta dos contenedores en la red `brasaland-net`: `uis` (website en el 3000 y backoffice en el 3001, con `next dev`, desde un único contenedor) y `api` (FastAPI con Uvicorn y `--reload`). Coinciden con la consigna:

- `uis/Dockerfile` sobre `node:22-alpine`, con las dependencias de cada app instaladas por separado y un `CMD` que invoca `start.sh`;
- `services/Dockerfile` sobre `python:3.12-slim`, que instala `uv`, instala las dependencias con `uv pip install -r requirements.txt` y arranca Uvicorn con `--reload`;
- los dos `.dockerignore` con, al menos, las exclusiones pedidas;
- `docker-compose.yml` en la raíz con dos servicios, bind mounts, los puertos expuestos y una red con nombre explícito;
- las variables en un `.env` en la raíz, ignorado por Git, y ningún secreto en los `Dockerfile` ni en el YAML;
- la comunicación entre servicios por su nombre (`http://api:8000/api/v1`).

Las diferencias vienen de la estructura del monorepo, de Windows y de un cambio en la consigna. Las decisiones se tomaron con el desarrollador el 16 y el 17 de noviembre de 2026.

> **Estado:** implementado y verificado en local (2026-11-17), con un commit por fase hecho por el desarrollador. El despliegue al VPS queda fuera de alcance ([apartado 1](#1-sin-despliegue-al-vps)).

| Qué | Consigna | Implementación | Motivo principal |
| --- | --- | --- | --- |
| Despliegue a producción | Desplegar el stack en el VPS y aportar evidencia | Fuera de alcance; sin modo de producción ni `docker-compose.prod.yml` | Ese apartado se eliminó de la consigna |
| Paquetes locales | — | `packages/shared` y `packages/brasa-core` llegan a las imágenes como `additional_contexts` de Compose, y las imágenes reproducen la estructura `/repo/...` | Están fuera de `/uis` y `/services`, que son los contextos de build que pide la consigna |
| `requirements.txt` | La API instala desde `requirements.txt` | `services/requirements.txt` se genera desde `uv.lock`; el paquete local `brasaland-shared` se instala aparte, en modo editable | La API gestiona sus dependencias con `pyproject.toml` y `uv.lock`; así no hay dos fuentes de verdad |
| Next.js en Docker | `next dev` para ambas apps | `next dev --webpack` en el contenedor; fuera de Docker sigue Turbopack | Turbopack (Next 16.3.5) no detecta los cambios en los bind mounts |
| Sondeo de archivos | — | `watchOptions.pollIntervalMs` en los dos `next.config.ts` (solo si existe `NEXT_WATCH_POLL_INTERVAL_MS`) y `WATCHFILES_FORCE_POLLING` en la API | Docker Desktop no propaga los eventos de archivos de Windows ni de macOS |
| Puesta en marcha | `docker compose up` "sin pasos adicionales" | `cp .env.example .env` y rellenar los secretos, una vez; después, `docker compose up` | Los secretos no pueden estar en el repositorio |
| Pull Request | Desde la rama hacia `main` | Contra `feature/backoffice-navigation`, la rama anterior de la cadena | Los PR anteriores siguen abiertos; al fusionarlos, GitHub cambia el destino a `main` |

### 1. Sin despliegue al VPS

La consigna original pedía desplegar los contenedores en el VPS de etapas anteriores y aportar evidencia (`docker compose ps` por SSH o una URL en vivo). El desarrollador confirmó el 16 de noviembre que ese apartado se eliminó de la consigna. Por eso no hay modo de producción: ni `docker-compose.prod.yml`, ni imágenes con `next build`, ni variables de producción. El criterio de evaluación 8 no aplica.

### 2. Paquetes locales fuera de los contextos de build

La consigna construye cada imagen desde su carpeta (`/uis` y `/services`), pero dos dependencias viven en `packages/`: la API instala `brasaland-shared` desde `../../packages/shared`, y el backoffice depende de `file:../../packages/brasa-core`. Docker no puede copiar nada fuera de su contexto. Las alternativas eran peores:

- construir desde la raíz ignoraría los `.dockerignore` de `/uis` y `/services` que pide la consigna;
- copiar los paquetes dentro de cada carpeta duplicaría código;
- publicarlos en un registro añadiría infraestructura para dos paquetes internos.

Con `additional_contexts`, Compose entrega cada paquete como un contexto con nombre (`shared` y `brasa-core`). Las imágenes reproducen la estructura del monorepo bajo `/repo`, así que las rutas relativas de `pyproject.toml` y `package.json`, y la raíz de Turbopack del backoffice, siguen siendo válidas. En desarrollo, los dos paquetes también se montan con bind mounts, así que sus cambios se ven sin reconstruir.

### 3. `requirements.txt` generado desde `uv.lock`

La API no tenía `requirements.txt`: sus dependencias están en `pyproject.toml`, fijadas en `uv.lock`. Para cumplir `uv pip install -r requirements.txt` sin mantener dos listas a mano, `services/requirements.txt` se genera con `uv export --frozen --no-dev --no-hashes` (el comando exacto está en su cabecera). Excluye el propio proyecto y `brasaland-shared`: el `Dockerfile` instala este último aparte, en modo editable. `uv` 0.13.7, la misma versión que se usa en local, se copia desde la imagen oficial de Astral (`ghcr.io/astral-sh/uv`), el método que recomienda su documentación.

**Coste:** si cambian las dependencias de la API, hay que regenerar `requirements.txt` y reconstruir la imagen.

### 4. Next.js con webpack en Docker

La consigna pide `next dev` para las dos apps. Next 16 usa Turbopack por defecto, y la verificación mostró que Turbopack no detecta los cambios en los bind mounts:

- ni con sondeo (`watchOptions.pollIntervalMs`, cargado correctamente);
- ni sin él;
- ni con cambios hechos dentro del propio contenedor.

En el host, la misma prueba sí funciona. Con `next dev --webpack` y sondeo, un cambio hecho desde Windows se ve sin reconstruir. `start.sh` arranca así las dos apps. Webpack lee el mismo `watchOptions.pollIntervalMs` de `next.config.ts`, así que no hacen falta más cambios. Fuera de Docker, `npm run dev` sigue con Turbopack.

**Coste:** en Docker compila otro bundler que en el host (algo más lento, y con alguna diferencia posible de comportamiento). `next build` no cambia. Si una versión futura de Next corrige el sondeo de Turbopack, basta con quitar `--webpack` de `start.sh`.

### 5. Sondeo de archivos

Docker Desktop no propaga a los contenedores los eventos de archivos de Windows: el contenido cambiado llega, pero el aviso de cambio no (se comprobó con `fs.watch` en un bind mount). Sin sondeo, ninguna de las dos recargas en caliente funcionaría. La API usa `WATCHFILES_FORCE_POLLING=true`. En Next.js, la variable habitual, `WATCHPACK_POLLING`, no la lee Turbopack, así que los dos `next.config.ts` activan `watchOptions.pollIntervalMs` solo si existe `NEXT_WATCH_POLL_INTERVAL_MS`. La define Compose (1000 ms), así que fuera de Docker no cambia nada.

**Coste:** el sondeo consume algo de CPU mientras el stack está en marcha.

### 6. Un paso previo: crear el `.env`

El criterio 1 pide levantar la plataforma "sin pasos adicionales de configuración". La API necesita secretos (`SECRET_KEY`, `DATABASE_URL` de Supabase y `RESEND_API_KEY`), y la propia consigna prohíbe versionarlos. Por eso hay un único paso previo, una sola vez: `cp .env.example .env` y rellenar los secretos. Los valores no secretos ya vienen en `.env.example`. Si falta una variable obligatoria, Compose se detiene con un mensaje que la nombra (`${VAR:?mensaje}`), en lugar de arrancar una API que fallaría.

### 7. Pull Request contra la rama anterior

La consigna pide abrir el PR hacia `main`. La rama parte de `feature/backoffice-navigation` porque los PR #8 a #16 siguen abiertos, como en las entregas anteriores. El PR apunta a esa rama para mostrar solo los cambios de este ticket; al fusionar la cadena en orden, GitHub cambia su destino a `main`.

### 8. Decisiones de funcionamiento

Estas decisiones no se apartan de la consigna, pero concretan lo que no especifica.

| Decisión | Motivo | Límite conocido |
| --- | --- | --- |
| Cada servicio recibe solo sus variables, con `environment:` y `${VAR}`, en lugar de un `env_file` compartido | Mínimo privilegio: el frontend no recibe los secretos de la API | Una variable nueva hay que añadirla también al YAML |
| Obligatorias con `${VAR:?mensaje}`; opcionales con `${VAR:-}` | Un error claro antes de arrancar; la API trata los opcionales vacíos como ausentes | Compose exige las obligatorias en cualquier comando, también en `down` |
| Healthcheck de `api` contra `/health`, y `uis` espera a que esté sana | El backoffice no arranca contra una API caída | Si la API no arranca (por ejemplo, sin acceso a Supabase), `uis` tampoco |
| Usuarios sin privilegios: `brasaland` (uid 1000) en la API y `node` en las interfaces | Buena práctica; se comprobó que pueden escribir en los bind mounts desde Windows | — |
| Volúmenes anónimos para `node_modules`, `.next` y el `.venv` de la API | Los binarios de Linux no se mezclan con los del host, y el sondeo no recorre el `.venv` | Tras cambiar dependencias: `docker compose up --build --renew-anon-volumes` |
| `start.sh` prefija la salida (`[website]`, `[backoffice]`), reenvía `SIGTERM` y `SIGINT`, y termina con error si una app se cae | Logs legibles, parada limpia (1 s) y un contenedor que no queda a medias | — |
| `.dockerignore` con exclusiones extra: entornos y cachés locales, cobertura y las bases TinyDB | Imágenes más pequeñas y sin datos locales | — |
| Los datos TinyDB se comparten con el host por el bind mount | Mismos usuarios y proveedores dentro y fuera de Docker | La API del host y la del contenedor escriben en los mismos archivos: conviene no tener las dos en marcha a la vez |
| Next.js carga `uis/backoffice/.env.local` desde la carpeta montada | Es el comportamiento de Next; las variables de Compose tienen prioridad (comprobado) | Una variable que solo esté en `.env.local` también llega al contenedor |
| Los scripts de la API se lanzan con `python -m` o `python -c` (por ejemplo, `create-admin`) | La imagen instala las dependencias, no el proyecto, así que los atajos de `uv run` no existen | Comandos más largos; están en el README raíz |

### 9. Cómo verificarlo

Ejecutado el 17 de noviembre de 2026 en Windows 11 con Docker Desktop 29.9.3 (Compose v5.7.0). Hay una fila por cada criterio de evaluación de la consigna.

| Criterio | Comando o acción | Resultado |
| --- | --- | --- |
| 1. `docker compose up` levanta la plataforma sin errores ni pasos adicionales | Con el `.env` creado: `docker compose down -v`, `docker compose build --no-cache` y `docker compose up -d`; `docker compose ps` | `api` healthy y `uis` en marcha, sin pasos manuales. Responden 200 `localhost:3000`, `/registro`, `localhost:3001`, `/login`, `/funciones`, `localhost:8000/docs` y `/health`. Único paso previo: el `.env` ([apartado 6](#6-un-paso-previo-crear-el-env)) |
| 2. Los cambios del host se ven sin reconstruir | Cambios temporales desde Windows, revertidos después, en `services/brasaland-api/app/main.py` (`/health`), el título del website y el de `/login` del backoffice | WatchFiles recarga la API, y las dos apps sirven el título nuevo en segundos. Con Turbopack las apps no se recargaban: ver el [apartado 4](#4-nextjs-con-webpack-en-docker) |
| 3. Las dos apps en puertos distintos desde un único contenedor | `docker compose ps`; logs de `uis` | Un contenedor `uis` publica el 3000 y el 3001; la salida lleva el prefijo `[website]` o `[backoffice]` |
| 4. Comunicación por nombre de servicio | `docker compose exec uis wget -qO- http://api:8000/health`; desde `api`, `http://uis:3001/login`; login real por el BFF con una cuenta temporal | `{"status":"ok"}` y 200. Por `localhost:3001/api/...`: registro 201, login 200, `/auth/me` 200, `/inventory/products` 200 (6 ingredientes, solo lectura en Supabase), borrado de la cuenta 200 y login posterior 401. El log de la API muestra todas las peticiones desde la IP del contenedor `uis` |
| 5. Sin secretos en `Dockerfile` ni en `docker-compose.yml` | Búsqueda de los valores reales del `.env` en todos los archivos versionados; revisión de los `Dockerfile`, el YAML y `.env.example` | Ningún valor real aparece en el repositorio; el YAML solo usa `${VAR}` y `.env.example` deja vacíos los secretos |
| 6. `.env` en el `.gitignore` y fuera del historial | `git check-ignore -v .env`; `git log --all -- .env` | Ignorado por `.gitignore:2:.env*`; ningún commit lo contiene |
| 7. Existen `.dockerignore` en `/uis` y `/services` | Revisión de los archivos y del contenido de las imágenes | Los dos existen con las exclusiones pedidas; las imágenes no llevan `.env`, `node_modules` ni `.next` del host, `tests/`, cobertura ni bases TinyDB |
| 8. Contenedores en producción en el VPS | — | No aplica: el apartado se eliminó de la consigna ([apartado 1](#1-sin-despliegue-al-vps)) |
| Sin regresiones | `uv run pytest` en `services/brasaland-api`; `npm test`, `npx tsc --noEmit` y `npx eslint next.config.ts` en las dos apps | 916 y 163 pruebas pasan; `tsc` y `eslint` sin errores |

---

## Auditoría de rendimiento de ambos frontends

Ciclo medir → analizar → corregir → volver a medir sobre `uis/website` y `uis/backoffice`, en la rama `feature/performance-audit`. Coincide con la consigna:

- Lighthouse antes y después en modo producción (`build` + `start`), con capturas en `audit/before/` y `audit/after/`;
- website en escritorio y móvil (`/` y `/registro`) y backoffice en su vista con más datos (`/gestor-incidencias`) y su portada;
- `AUDIT.md` con las puntuaciones iniciales, la causa raíz de cada problema y el análisis de refactorización (3 casos);
- correcciones de una en una, cada una con su commit y su medición;
- un hook y dos componentes extraídos e integrados;
- `REPORT.md` con la comparativa y la valoración.

Las diferencias vienen de cómo se midió y de lo que la medición demostró. Las decisiones se tomaron con el desarrollador el 17 de noviembre de 2026.

> **Estado:** completado (2026-11-17), un commit por fase y por corrección, hechos por el desarrollador. Resultado y comprobación de los criterios de evaluación en [`audit/REPORT.md`](../audit/REPORT.md#9-criterios-de-evaluación).

| Qué | Consigna | Implementación | Motivo principal |
| --- | --- | --- | --- |
| Ubicación de los informes | `AUDIT.md` y `REPORT.md`, sin carpeta indicada | `audit/AUDIT.md` y `audit/REPORT.md`, junto a `audit/before/` y `audit/after/` | Toda la auditoría en una carpeta; AGENTS.md pide no llenar la raíz |
| "Producción" | Medir el servidor de producción | `build` + `start` de cada app en local, fuera de Docker | No hay despliegue público; el contenedor de desarrollo usa `next dev`, que la consigna invalida |
| Herramienta de medición | Lighthouse en DevTools | Capturas con DevTools y cifras con Lighthouse CLI (mediana de 3) | Una sola ejecución varía demasiado para comparar correcciones pequeñas |
| Versión de Lighthouse | — | Fijada en 13.5.0, la de DevTools en Chrome 157 | Con 13.6.0 el LCP simulado en móvil cambiaba de 2,5 s a 0,8 s sobre el mismo código |
| Categorías | Performance, Accessibility, Best Practices, SEO | Las cuatro; se excluye Agentic Browsing, que Lighthouse 13 añade | No mide rendimiento ni la experiencia de las personas |
| Backoffice en móvil | La consigna solo pide los dos modos para el sitio corporativo | Backoffice solo en escritorio | Es una herramienta interna que se usa a diario en escritorio |
| Skills | Instalar una o más de las tres propuestas | `core-web-vitals` y `performance`; no `web-perf` | `web-perf` se centra en la red de borde y la caché de Cloudflare, que aquí no aplican |
| Correcciones "requeridas" | Aplicar las que las skills clasifiquen como requeridas | Las skills no etiquetan; se derivó un criterio de su método. Una requerida (P2) se midió y se revirtió | La medición demostró que no mejoraba y empeoraba el escritorio |
| Next.js 16.4.6 | — | Fuera de alcance | Cambiar de versión entre el "antes" y el "después" contaminaría la comparación |
| Pull Request | Desde la rama hacia `main` | Contra `feature/dockerize`, la rama anterior de la cadena | Los PR anteriores siguen abiertos; al fusionarlos, GitHub cambia el destino a `main` |

### 1. Ubicación de los informes

La consigna fija las carpetas de las capturas (`/audit/before/` y `/audit/after/`), pero no dónde van `AUDIT.md` y `REPORT.md`. Se guardan en `audit/` para tener toda la auditoría en una carpeta y no sumar archivos a la raíz del monorepo, como pide `AGENTS.md`.

### 2. Medición en local y con dos herramientas

**Servidor.** No existe un despliegue público de estas apps. Se mide su build de producción servido en local (`npm run build` + `npm run start`), lo más fiel posible a la consigna. El contenedor de Docker del monorepo no sirve para medir porque arranca `next dev`. Consecuencias, documentadas en `AUDIT.md`:

- el TTFB observado en local (5–10 ms) no es representativo de una red real;
- no hay datos de campo (CrUX) para `localhost`.

**Herramientas.**

- Las capturas, que pide la consigna, las hizo el desarrollador con DevTools.
- Las cifras de las tablas son la mediana de 3 ejecuciones del CLI de Lighthouse, con perfil limpio en cada una, las mismas condiciones y los JSON guardados. La skill `performance` exige esa mediana para decidir sobre una métrica, y la medición lo confirmó: en el gestor, el CLS variaba entre 0,065 y 0,204 de una ejecución a otra.
- En el backoffice, el script inyecta el token de una cuenta temporal (rol `user`) sin cargar ninguna página de la app. Esa cuenta se borró al terminar.

**Versión fijada.** El CLI se fijó en Lighthouse 13.5.0, la versión que trae DevTools en Chrome 157. Con 13.6.0 el LCP simulado en móvil salía 0,76 s frente a 2,4 s en DevTools, con el mismo elemento y las mismas condiciones. Los informes exportados de DevTools están en `audit/before/devtools-*.json`.

### 3. Agentic Browsing y backoffice en escritorio

- **Agentic Browsing:** Lighthouse 13 añade esta quinta categoría. Se excluye porque la consigna pide cuatro puntuaciones y porque evalúa si un agente de IA puede usar la página, no el rendimiento.
- **Backoffice:** la consigna pide escritorio y móvil solo para el sitio corporativo. El backoffice se mide en escritorio, donde se usa a diario.

### 4. Skills instaladas y criterio de "requerido"

- **Qué se instaló:** `core-web-vitals` y `performance`, de `addyosmani/web-quality-skills@afa8da9`, leídas completas antes de instalarlas: son solo Markdown, sin scripts.
- **Dónde:** en `.claude/skills/` del proyecto, sin commit (excluidas en `.git/info/exclude`). La evidencia de uso está en `AUDIT.md` y `REPORT.md`.
- **Lo que no se instaló:** `web-perf` (Cloudflare) se centra en la red de borde y la caché de ese proveedor.

Las skills no etiquetan sus hallazgos como "requeridos" o "sugerencias"; separan métricas medidas de hipótesis del código. Se derivó el criterio de su método:

- **requerido:** una métrica o auditoría que falla o está en el umbral, con su causa demostrada;
- **sugerencia:** lo que sale de su checklist sin medición que lo respalde.

### 5. Una corrección requerida que se revirtió (P2)

P2 (LCP en móvil de 2,54 s en la home) cumplía el criterio de requerido. La corrección prevista era quitar `loading="eager"` a la foto de la fachada, que en móvil queda bajo el pliegue. Se aplicó y se midió con 5 ejecuciones por modo:

- el LCP en móvil no cambió;
- en escritorio, donde esa foto es el LCP, Lighthouse pasó a marcar "LCP resources should not use loading=lazy".

Se revirtió y no lleva commit; el análisis completo está en `REPORT.md` §3.2. Aplicarla igualmente habría sido un cambio superficial, justo lo que la consigna pide evitar.

### 6. Fuera de alcance

- **Next.js 16.4.6:** la actualización de seguridad pendiente se aplicará cuando se fusione la cadena de PR, y conviene volver a medir entonces con la misma versión de Lighthouse.
- **Problemas P4 y P5:** el CSS que bloquea el render y el JS del framework no se corrigen. Exigirían cambiar la arquitectura o la compilación, y la consigna prohíbe reestructurar.

### 7. Pull Request contra la rama anterior

La rama sale de `feature/dockerize` porque el PR #17 sigue abierto. El PR de esta auditoría apunta a esa rama y GitHub cambiará su destino a `main` cuando se fusionen los anteriores, como en el resto de la cadena.

## Auditoría de serialización del backend

Revisión de los 35 endpoints de `services/brasaland-api` para que cada uno tenga un esquema de respuesta explícito, ajustado a su consumidor y sin campos sensibles, en la rama `feature/serialization-audit`. Coincide con el briefing en lo siguiente:

- auditoría escrita en `docs/serialization-audit.md`, con la clasificación ✅/⚠️/❌, el estado original y los cambios;
- las rutas de auth al principio;
- esquemas de salida con atributos nombrados y esquemas de entrada separados;
- listados ligeros;
- el registro no reenvía el email, y `GET /auth/me` sí devuelve el del propio usuario;
- decisiones sobre relaciones documentadas.

Las decisiones se tomaron con el desarrollador el 18 de noviembre de 2026.

> **Estado:** completada (2026-11-18), un commit por fase y subfase, hechos por el desarrollador. Los 35 endpoints quedan ✅. La verificación (pruebas, comparación del OpenAPI y prueba manual en `/docs`) está en [`docs/serialization-audit.md`](serialization-audit.md#8-verificación).

| Qué | Briefing | Implementación | Motivo principal |
| --- | --- | --- | --- |
| Exportación CSV | "Cada endpoint de la API debe tener un serializer de respuesta explícito" | `GET /api/v1/incidents/results/export` declara `response_model=None` y documenta `text/csv` en OpenAPI | La respuesta es un archivo, no JSON |
| Destino del PR | No lo indica | `feature/performance-audit`, la rama anterior de la cadena | Los PR #17 y #18 siguen abiertos |

### 1. La exportación CSV no tiene esquema Pydantic

El briefing pide un serializer de respuesta explícito en cada endpoint. `GET /incidents/results/export` devuelve el archivo `results.csv` que exige el briefing del analizador de incidentes (Fase 2), con `Content-Disposition: attachment`. Un modelo Pydantic describe JSON, no un archivo, así que no hay esquema que declarar sin romper esa descarga.

Para que la excepción sea explícita y no un olvido:

- el decorador declara `response_model=None` con un comentario que remite a la auditoría;
- OpenAPI documenta la respuesta 200 como `text/csv`, con las columnas `metric`, `value` y `percentage`, y una prueba lo comprueba;
- la prueba de guarda de la subfase 2d acepta esta ruta como única excepción, con nombre propio.

**Coste:** el contrato de esta ruta lo fija la prueba de las columnas del CSV, no un esquema. Es el mismo contrato que ya tenía.

### 2. Pull Request contra la rama anterior

La rama sale de `feature/performance-audit` porque los PR #17 y #18 siguen abiertos. El PR de esta auditoría apunta a esa rama, y GitHub cambiará su destino a `main` cuando se fusionen los anteriores, como en el resto de la cadena.

## Estrategia de caching

Análisis y optimización de caching de la API y del backoffice, en la rama `feature/caching-optimisation`. Coincide con el briefing en lo siguiente:

- middleware de timing con el formato del enunciado;
- seeder de volumen realista, con las filas de antes y después;
- dos endpoints cacheados con TTL e invalidación en las escrituras;
- ningún dato privado en una clave compartida;
- dos componentes con `next/dynamic` y un `useMemo` sobre un cálculo no trivial;
- `CACHING_REPORT.md` con las cuatro secciones pedidas.

El informe está en [`docs/CACHING_REPORT.md`](CACHING_REPORT.md). Las decisiones se tomaron con el desarrollador el 18 de noviembre de 2026.

> **Estado:** completada (2026-11-18), un commit por fase, hechos por el desarrollador.

| Qué | Briefing | Implementación | Motivo principal |
| --- | --- | --- | --- |
| Middleware de timing | "Añade esto a tu `main.py`" | `app/core/timing.py` (`register_timing_middleware`), registrado en `main.py` | Mismo patrón que `register_error_handlers`, y se puede probar aparte |
| Evidencia del `useMemo` | "Aplícalo solo cuando el perfilado muestra que el cálculo es genuinamente costoso" | Coste del cálculo medido con `performance.now()` en Chrome, a CPU x1 y x4; beneficio estimado, no medido con el Profiler de React | El build de producción no expone el Profiler; se midió el cálculo que se evita |
| Destino del PR | No lo indica | `feature/serialization-audit`, la rama anterior de la cadena | Los PR #17, #18 y #19 siguen abiertos |

### 1. Middleware de timing en `app/core/timing.py`

El enunciado pega el middleware directamente en `main.py`. Aquí vive en `app/core/timing.py`, y `main.py` solo lo registra con `register_timing_middleware(app)`, igual que los manejadores de errores (`register_error_handlers`).

El formato de la línea y el logger (`api.timing`) son los del briefing. Hay dos añadidos:

- **un handler de consola:** uvicorn solo configura sus propios loggers, así que sin él las líneas de INFO no salen;
- **los errores no controlados se registran como 500:** sin este añadido, esas peticiones no aparecerían en la medición.

Las 5 pruebas de `tests/core/test_timing.py` montan el middleware sobre una app mínima, cosa que no sería posible si estuviera definido dentro de `main.py`.

**Coste:** ninguno. Quien busque el middleware en `main.py` encuentra allí la llamada que lo registra.

### 2. El `useMemo` se justifica midiendo el cálculo, no con el Profiler

El briefing pide aplicar `useMemo` cuando el perfilado demuestra que el cálculo es costoso, y menciona el Profiler de React DevTools. La medición se hizo con Chrome sin cabeza contra el build de producción, que no expone el Profiler. Se midió directamente el cálculo que el `useMemo` evita repetir:

- filtrar y contar 21 140 órdenes cuesta 4,9 ms en escritorio;
- con la CPU ralentizada 4 veces cuesta 31,8 ms, más de un fotograma.

Se descartaron los cálculos triviales, como el recuento por tipo (0,26 ms). El beneficio por clic en "Mostrar más" (~30 ms en un móvil) es una estimación a partir de ese coste. El informe lo dice así (`CACHING_REPORT.md`, §4.4 y §7).

**Coste:** el beneficio del `useMemo` está estimado, no medido como tiempo de render en React.

### 3. Pull Request contra la rama anterior

La rama sale de `feature/serialization-audit` porque los PR #17, #18 y #19 siguen abiertos. El PR de esta tarea apunta a esa rama, y GitHub cambiará su destino a `main` cuando se fusionen los anteriores, como en el resto de la cadena.

## Plan de Telemetría

Plan de diseño de la telemetría de la plataforma, en la rama `feature/telemetry-plan`: `docs/telemetry/telemetry-plan.md` y `docs/telemetry/event-schemas.json` (JSON Schema draft-07), sin código de instrumentación. Coincide con el briefing y con el enunciado en lo siguiente:

- las 6 métricas obligatorias, con sus `event_type`, hipótesis, decisiones y propiedades mínimas;
- el envelope con los nombres literales del enunciado (`eventId`, `timestamp`, `sessionId`, `userId`, `event_type`, `schemaVersion`, `requestId`, `properties`);
- la taxonomía `entidad_acción`, el allowlist por evento, los datos sensibles con su tratamiento, la decisión stream/batch, el throttle y los riesgos y exclusiones;
- las restricciones de negocio: moneda del local sin conversión, stock solo por órdenes, idioma de la interfaz separado de `country`, sin nombres de empleados ni datos de clientes.

Las decisiones se tomaron con el desarrollador el 18 de noviembre de 2026.

> **Estado:** completado (2026-11-18), un commit por fase, hechos por el desarrollador.

| Qué | Briefing o enunciado | Implementación | Motivo principal |
| --- | --- | --- | --- |
| Instrumentación de las métricas obligatorias | "Impleméntalas sin falta" (mensaje del tech lead) | Diseñadas en el plan, sin código; la sección 12 lista los cambios de modelo que necesitan | El mismo mensaje dice "no escribas código todavía", y el briefing pide que estén instrumentadas "al final de la serie" |
| Propiedades mínimas en `direct_stock_edit_rejected` | Campos mínimos de los eventos de inventario: `location_id`, `country`, `product_id`, `product_category`, `quantity`, `unit`, `currency` | Opcionales en este evento; obligatorias en los otros 5 | Un intento sobre `/products/{id}` no tiene local, cantidad ni moneda |
| Destino del PR | Rama oculta en la captura; "PR aprobado → merge a `main`" | `feature/caching-optimisation`, la rama anterior de la cadena | Los PR #17 a #20 siguen abiertos |

### 1. Las métricas obligatorias se diseñan, no se instrumentan todavía

El mensaje del tech lead dice "impleméntalas sin falta" y, a continuación, "no escribas código todavía — escribe el plan que el equipo va a implementar mañana". El briefing sitúa la instrumentación "al final de la serie de proyectos" (captura → almacenamiento). Por eso las 6 métricas están en el plan con su disparo exacto en la API, su esquema y su estrategia de entrega, pero sin código.

Además, 4 de ellas no se pueden emitir con el modelo actual: faltan el coste unitario de las entradas, el motivo de la merma, los mínimos por local y la entidad de locales. El plan lo dice en la sección 12 (brechas B3 a B8) en lugar de rellenar esos campos con valores inventados.

**Coste:** ninguno para esta fase; la instrumentación es la tarea de la siguiente.

### 2. Propiedades mínimas opcionales en `direct_stock_edit_rejected`

El briefing pide `location_id`, `country`, `product_id`, `product_category`, `quantity`, `unit` y `currency` en los eventos de inventario. En `direct_stock_edit_rejected` el intento puede no tener esos datos: un `PATCH /api/v1/inventory/products/{id}` no indica local ni cantidad, y la moneda depende del local. Hacerlas obligatorias obligaría a inventarlas o a no emitir el evento.

Son obligatorias en los otros 5 eventos obligatorios. En este son opcionales y se rellenan cuando la petición los trae. La brecha B10 propone asignar un local a cada cuenta para atribuir siempre el intento al local de quien lo hace, que es la decisión que pide el briefing.

**Coste:** hasta cerrar B10, los intentos sobre `/products/{id}` no se pueden agregar por local.

### 3. Pull Request contra la rama anterior

El enunciado oculta la rama destino y recuerda hacer merge a `main` antes de empezar la rama siguiente. Los PR #17 a #20 siguen abiertos, así que esta rama sale de `feature/caching-optimisation` y el PR apunta a ella, con el título exacto `docs: telemetry design plan`. GitHub cambiará su destino a `main` cuando se fusionen los anteriores, como en el resto de la cadena.

---
## Captura de eventos de telemetría

Primera implementación del plan de telemetría, en la rama `feature/telemetry-capture`. El backoffice captura los eventos con un `TelemetryService` (`uis/backoffice/lib/telemetry/`) y los envía en lotes a un receptor provisional de la API (`POST /telemetry/events`), que valida el formato y responde `{"received": N}` sin guardar nada. Coincide con el enunciado en lo siguiente:

- **Receptor:** el router propio en `services/`, el modelo Pydantic `TelemetryEvent` con los campos del envelope, el log con la cantidad y el `event_type` de cada evento, `TELEMETRY_ENDPOINT` en la configuración del backend y la URL del frontend en `NEXT_PUBLIC_TELEMETRY_ENDPOINT`.
- **Servicio:** una única función pública `track(eventType, properties)`; cola local; lotes de 20 eventos o cada 10 s; `sendBeacon` en `visibilitychange`; 3 reintentos con espera exponencial; `eventId`, `sessionId`, `userId`, `timestamp`, `schemaVersion` y `requestId` puestos por el servicio.
- **Eventos:** todas las métricas obligatorias, el piso técnico (errores de JavaScript, rendimiento y vistas), los eventos de negocio, con los nombres y el allowlist de `event-schemas.json`, sin PII.
- **Actividad adicional:** Web Vitals con `useReportWebVitals` y la autenticación capturada en sus módulos, con la razón del login fallido y sin email ni contraseña.

Las decisiones (C1 a C9) se tomaron con el desarrollador el 19 de noviembre de 2026. El plan (`docs/telemetry/telemetry-plan.md`, sección 13) y el esquema (catálogo 1.1.0) se actualizaron con ellas antes de escribir código.

> **Estado:** completado y verificado en DevTools (2026-11-19), un commit por fase, hechos por el desarrollador.

| Qué | Briefing o enunciado | Implementación | Motivo principal |
| --- | --- | --- | --- |
| Emisor de los eventos que el plan asignaba a la API | Plan: 32 eventos emitidos por la API | 26 pasan al navegador (`source: "browser"`), emitidos al recibir la respuesta de la API | El enunciado pide capturarlos en el backoffice con `track()` |
| Ruta del receptor | `POST /telemetry/events` | `POST /telemetry/events`, fuera de `/api/v1`, pública, con CORS solo para el backoffice | Coincide con la consigna; se aparta de la convención `/api/v1` de la API |
| Ubicación del servicio | `uis/backoffice/src/services/telemetry.ts` (o equivalente) | `uis/backoffice/lib/telemetry/` | El backoffice no tiene `src/`; sus clientes viven en `lib/` |
| Campos de `TelemetryEvent` | 8 campos del envelope | Los 8, más `source` y `environment` | Son parte del envelope aprobado en el plan |
| Motivos de `login_failed` | `invalid_credentials`, `session_expired`, `network_error` | `invalid_credentials`, `inactive_user`, `network_error`; la sesión caducada es `session_expired` | Un intento de login no caduca; la cuenta desactivada sí es un motivo real |
| Alcance | "Cada evento de tu catálogo" / "tantas como te alcance el día" | 34 de 44; 10 esperan al emisor de la API | Sin control en el backoffice o con datos que solo tiene el servidor |
| Datos provisionales de los obligatorios | Mínimos por local, país del local, id del proveedor | Umbral de stock bajo por unidad sobre el stock global; país del ingrediente; id del directorio por nombre | Brechas B3, B7 y B8 del plan, abiertas |
| `direct_stock_edit_rejected` | Un usuario intenta modificar el stock directamente | Acción "Ajustar stock" que envía el cambio real y recibe el 405 | El backoffice no tenía ninguna forma de intentarlo |
| `sessionId` | "Generado al login y guardado en memoria de sesión" | Creado al iniciar sesión y guardado en `sessionStorage` | En memoria, cada recarga sería una sesión nueva |
| Huella de `frontend_error_captured` | Plan: SHA-256 truncado | FNV-1a de 64 bits | `crypto.subtle` no existe sin HTTPS |
| `page_performance_recorded` | Plan: uno por vista, con `data_ready_ms` | Uno por carga, sin `data_ready_ms` | Web Vitals solo mide la carga inicial |
| `updated_at` en el listado de incidencias | Auditoría de serialización: se quitó | Vuelve a `IncidentListItem` | `incident_status_changed` lo necesita |
| Destino del PR | Rama oculta en la captura | `feature/telemetry-plan` | Los PR #17 a #21 siguen abiertos |

### 1. Los eventos de la API se emiten en el navegador

El plan asignaba a la API 32 eventos, entre ellos las 6 métricas obligatorias, porque la API es la fuente de verdad. El enunciado de esta fase pide capturar cada evento del catálogo en el backoffice, con una única función `track()`, y deja el almacenamiento para la siguiente.

El backoffice los emite **al recibir la respuesta de la API**: un 2xx confirma que la operación ya está guardada (después del `commit`), y un rechazo trae su código de error. Así no se emite nada que el sistema no haya confirmado. Cada evento lleva el `requestId` de su llamada, que la API escribe en su línea de `api.timing`.

**Coste:** el riesgo R3 del plan queda asumido en esta fase. Una pestaña que se cierra antes de enviar o una orden registrada fuera del backoffice (con `curl`, por ejemplo) no dejan evento hasta que exista el emisor de la API. La cola, los reintentos y `sendBeacon` lo reducen. Se verificó el envío con `sendBeacon` al redirigir al login tras un 401.

### 2. El receptor está fuera de `/api/v1`

La ruta es la de la consigna, `POST /telemetry/events`, pero la API publica todos sus recursos bajo `/api/v1`. La recepción de telemetría es una vía de entrada aparte, no un recurso versionado del negocio. Además, el navegador la llama directamente, sin pasar por el BFF, y `sendBeacon` no puede enviar `Authorization`. Por eso es pública, como `/health`, y es la única ruta con CORS (`app/core/cors.py`), limitado a `POST` desde el origen de `FRONTEND_URL`. Los lotes de `sendBeacon` van como `text/plain`, porque no pueden enviar `application/json` a otro origen sin una comprobación previa de CORS; el receptor los lee como JSON igualmente.

Se consideró quitar `/api/v1` de toda la API para unificar. Se descartó: es un cambio de arquitectura ajeno a esta tarea.

**Coste:** un endpoint público sin autenticación. Lo limitan su CORS, su lote máximo de 100 eventos y el 413 a más de 256 KB.

### 3. `lib/telemetry/` en lugar de `src/services/telemetry.ts`

El backoffice no tiene carpeta `src/`, y sus clientes de la API viven en `lib/` (`lib/api-client.ts`, `lib/inventory.ts`). Una carpeta `services/` nueva se confundiría con el `services/` del monorepo, que es el backend. `lib/telemetry/index.ts` exporta solo `track()`.

Los demás módulos del servicio son internos:
- la cola, la sesión y el envelope;
- `withRequestId`, para la capa de datos;
- el catálogo, que se genera desde `event-schemas.json`.

### 4. `TelemetryEvent` con `source` y `environment`

El enunciado enumera los 8 campos del envelope. El plan aprobado añade `source` (emisor) y `environment` (para no mezclar datos de prueba, como las semillas `VOL-`, con los reales). El modelo los incluye todos con sus tipos y dominios, y no admite campos extra. Así se reutiliza sin cambios cuando el receptor guarde los eventos. Una prueba valida con él los 44 ejemplos de `event-schemas.json`.

### 5. Motivos de `login_failed` (esquema 2.0.0)

La actividad adicional pone como ejemplos de motivo `invalid_credentials`, `session_expired` y `network_error`. Un intento de login no puede fallar por sesión caducada: ese hecho es `session_expired`, un evento propio que emite `apiFetch` ante un 401 `token_expired`. Los motivos son, por tanto, `invalid_credentials` (401), `inactive_user` (403, la cuenta desactivada) y `network_error` (sin conexión, o 502/504 del intermediario).

El esquema del plan exigía además `account_fingerprint` (HMAC del email con una clave del servidor) y `client_network` (IP truncada). El navegador no puede calcularlos sin enviar el email, así que la versión 2.0.0 los quita. Volverán con el emisor de la API.

### 6. Alcance: 34 de los 44 eventos

El enunciado pide capturar cada evento del catálogo y, a la vez, "tantas del resto de tu catálogo como te alcance el día". Se capturan los 34 que nacen o pueden observarse en el backoffice. Los otros 10 esperan al emisor de la API:
- **Sin control en el backoffice:** `product_created`, `user_access_changed` y `supplier_deleted`.
- **Necesitan datos que solo tiene el servidor:** `password_reset_requested` (si la cuenta existe y la huella del email) y `server_error_occurred` (tipo de excepción).
- **Solo existen dentro del servidor o de los scripts:** `cache_stats_recorded`, `email_delivery_failed`, `api_instance_started` y `data_seed_executed`.
- **Falta un dato:** `incident_report_exported`, por la brecha B13.

La sección 13.4 del plan los lista con su motivo, y la 13.6 dice dónde se captura cada uno de los 34.

### 7. Valores provisionales en las métricas obligatorias

Para emitir los 6 obligatorios sin inventar datos se cerraron las brechas B5 y B6: el coste unitario de las entradas y el motivo de la merma. Las dos columnas se añaden en Supabase con `services/brasaland-api/migrations/001_inventory_unit_cost_waste_reason.sql`. Tres brechas siguen abiertas y se cubren con lo que ya existe:
- **B3, mínimos por local:** `stock_threshold_triggered` usa el umbral de stock bajo del backoffice por unidad (40 kg, 25 litros, 100 unidades) sobre el stock global del producto.
- **B7, entidad de locales:** `country` y `currency` salen del país del ingrediente. Por eso una orden de un ingrediente de Estados Unidos registrada en el local 1 sale con `country: "US"`.
- **B8, id del proveedor en la entrada:** `supplier_id` se busca en el directorio por el nombre elegido, que es único.

**Coste:** hasta cerrar B3 y B7, el umbral y el país no se pueden agregar por local.

### 8. "Ajustar stock" para `direct_stock_edit_rejected`

El backoffice no tenía ninguna forma de intentar cambiar el stock directamente, así que la métrica no podía ocurrir desde la interfaz. La acción "Ajustar stock" de `/inventario/ingredientes` envía el `PATCH` real con `current_stock`. La API lo rechaza con 405, se emite el evento, y el modal explica que el stock solo cambia con órdenes, con enlaces a la entrada y a la salida. El rechazo lo sigue decidiendo el sistema. Chrome muestra ese 405 como error en la consola, como cualquier respuesta 4xx: es el comportamiento esperado.

### 9. `sessionId` en `sessionStorage`

El enunciado pide generarlo al iniciar sesión y guardarlo "en memoria de sesión". Se guarda en `sessionStorage`: en una variable en memoria, cada recarga (F5) empezaría una sesión nueva y falsearía las métricas por sesión. Es propio de cada pestaña y se borra al cerrar la sesión o cuando caduca. Antes del login vale `null`.

### 10. Huella de los errores: FNV-1a

El plan definía `error_fingerprint` como SHA-256 truncado. En el navegador, `crypto.subtle` solo existe con HTTPS o en `localhost`, y una tablet que abra el backoffice por la IP de la red local no lo tendría. La huella debe ser la misma en todos los dispositivos para agrupar el mismo fallo, así que es FNV-1a de 64 bits: los mismos 16 caracteres hexadecimales y síncrona. La descripción del esquema se actualizó.

### 11. `page_performance_recorded` una vez por carga

Web Vitals (`useReportWebVitals`) mide la carga inicial del documento, no las navegaciones sin recarga. Por eso hay un evento por carga del backoffice, con la ruta de esa carga, y no uno por cada vista. Se emite al ocultar la pestaña, cuando CLS e INP son definitivas, justo antes del envío con `sendBeacon`. Para eso, el listener de ocultación está en `window` y se ejecuta después de los de Web Vitals. `data_ready_ms`, opcional, todavía no se emite.

### 12. `updated_at` vuelve al listado de incidencias

La auditoría de serialización quitó `updated_at` de `IncidentListItem` porque ninguna pantalla lo leía. `incident_status_changed` necesita saber cuánto tiempo pasó la incidencia en su estado anterior (`minutes_in_previous_status`), y el listado es lo que tiene el gestor al cambiar el estado. Volver a pedir el detalle de cada incidencia sería una llamada extra solo para la telemetría. El cambio está registrado en `docs/serialization-audit.md`, sección 11, junto con el receptor de telemetría (la operación 36).

### 13. Pull Request contra la rama anterior

La rama sale de `feature/telemetry-plan` y el PR apunta a ella, porque los PR #17 a #21 siguen abiertos. El título es `feat: telemetry event capture`; el desarrollador indicó que puede ir con iniciales en mayúscula, porque no se evalúa.

### Verificación de los criterios

| Criterio | Cumplimiento | Evidencia |
| --- | --- | --- |
| El stub `POST /telemetry/events` existe, acepta arreglos con `TelemetryEvent` y devuelve `{ "received": N }` | ✅ | `app/domains/telemetry/router.py`; `tests/integration/test_telemetry_router.py`; en vivo, 200 `{"received": N}` |
| `TelemetryEvent` refleja el envelope con todos sus campos | ✅ | `app/domains/telemetry/schemas.py`; la prueba valida los 44 ejemplos de `event-schemas.json` |
| La URL se lee de `NEXT_PUBLIC_TELEMETRY_ENDPOINT`, sin hardcodear | ✅ | `lib/telemetry/config.ts`; sin la variable, la telemetría se desactiva |
| El backend declara `TELEMETRY_ENDPOINT` | ✅ | `app/core/config.py`, `.env.example`, `docker-compose.yml`; aviso al arrancar |
| Cola local, lote de 10 s o 20 eventos, `sendBeacon` y reintentos con backoff | ✅ | `lib/telemetry/queue.ts` y `lifecycle.ts`; `__tests__/telemetry/queue.test.ts`; `sendBeacon` verificado en DevTools |
| El servicio genera `eventId`, `sessionId`, `userId`, `timestamp`, `schemaVersion` y `requestId` | ✅ | `lib/telemetry/envelope.ts`, `session.ts` y `request-context.ts`; `__tests__/telemetry/track.test.ts` |
| No hay `fetch`/`axios` de telemetría fuera del servicio | ✅ | El único `fetch` de telemetría está en `lib/telemetry/` (cola y beacon); el resto del backoffice solo llama a `track()` |
| Todas las métricas obligatorias instrumentadas | ✅ | Las 6, en `lib/inventory.ts` y `lib/telemetry/api-events.ts`; `__tests__/inventory/telemetry.test.ts`; `inbound_order_created` visto en DevTools |
| Piso técnico transversal (errores, rendimiento, navegación) | ✅ | `TelemetryRoot` en el layout raíz (`page_viewed`, `frontend_error_captured`, Web Vitals) y `api_latency_recorded` en `apiFetch` |
| `event_type` y allowlists del plan, no genéricos | ✅ | `track()` descarta cualquier evento fuera del catálogo generado desde `event-schemas.json`; las propiedades de los 34 eventos cumplen el esquema |
| Sin PII (email, nombre, contraseña) | ✅ | Allowlists sin claves personales (prueba del catálogo); `login_failed` solo con el motivo; formularios solo con nombres de campo; mensajes de error saneados |
| La pestaña Network muestra lotes con el formato correcto y respuesta 200 | ✅ | Capturas de DevTools (Payload con `inbound_order_created` y Headers con `200 OK`), también del lote enviado con `sendBeacon` |
| Web Vitals con la ruta en `properties` (adicional) | ✅ | `page_performance_recorded` con `route`, LCP, CLS e INP |
| Autenticación en los hooks y componentes de auth, sin email ni contraseña (adicional) | ✅ | `lib/auth/api.ts`, `SessionProvider` y `apiFetch`; `__tests__/telemetry/auth-events.test.ts` |

---

## Almacenamiento de eventos de telemetría

Segunda implementación del plan de telemetría, en la rama `feature/telemetry-storage`. El receptor `POST /telemetry/events` deja de ser provisional: valida cada evento por separado, guarda los válidos en la tabla `telemetry_events` de Supabase con una sola sentencia por lote y responde `{"received", "stored", "rejected"}`. El backoffice no cambia. Coincide con el enunciado en lo siguiente:

- **Tabla:** `telemetry_events` en Supabase con las ocho columnas (`id`, `timestamp`, `service`, `event_type`, `level`, `value`, `message` y `tags` en JSONB), los tres índices (`timestamp`, `event_type` y GIN en `tags`) y sin lógica de `UPDATE` ni `DELETE`.
- **Receptor:** la misma URL y el mismo lote `{"events": [...]}`, leído de forma laxa; cada evento se valida con `TelemetryEvent.model_validate`, el modelo de la fase anterior sin cambios; los inválidos se rechazan uno a uno sin cancelar el lote; los válidos se insertan con una única sentencia; la respuesta lleva `received`, `stored` y `rejected`.
- **`tags`:** el objeto `properties` del envelope, solo con las claves del allowlist, que conserva las dimensiones del briefing (`location_id`, `country`, `product_id`, `product_category`, `quantity`, `unit`, `currency`, `supplier_id`, `reason`).
- **Frontend:** ni una línea cambiada; `NEXT_PUBLIC_TELEMETRY_ENDPOINT` sigue apuntando a `http://localhost:8000/telemetry/events`.

Las decisiones (S1 a S11) se tomaron con el desarrollador el 19 de noviembre de 2026. El plan (`docs/telemetry/telemetry-plan.md`, sección 14) y el esquema (catálogo 1.2.0) se actualizaron con ellas antes de escribir código.

> **Estado:** completado y verificado de punta a punta con Supabase (2026-11-19), un commit por fase, hechos por el desarrollador.

| Qué | Briefing o enunciado | Implementación | Motivo principal |
| --- | --- | --- | --- |
| Estructura de la tabla | "Con la siguiente estructura" (la tabla no aparece en la página del enunciado) | Las ocho columnas, índices y mapeo de un documento de la academia | Es el contrato que piden los criterios ("las ocho columnas") |
| Reglas de `service`, `level`, `value` y `message` | "Ajusta las reglas al plan del estudiante" | `service` sale de `source`; `level`, `value` y `message`, de anotaciones `x-*` por evento en `event-schemas.json` | Una sola fuente para el plan, el esquema y el receptor |
| Restricciones de la tabla | `level` con default `'info'`; `tags` con default `'{}'` | Además, `NOT NULL` en los dos y `CHECK` de `level` a `info`, `warn` y `error` | La base no admite valores fuera del dominio |
| `id` de la fila | Default `gen_random_uuid()` | El `eventId` del envelope (el default se conserva), con `ON CONFLICT (id) DO NOTHING` | Los reintentos y los `sendBeacon` repetidos no duplican filas |
| Campos del envelope | "Pueden ir en `tags` si el plan los necesita" | `session_id`, `user_id`, `request_id`, `schema_version` y `environment` en `tags` | Los análisis por sesión y usuario, la correlación con la API y separar entornos |
| Validación del evento | `TelemetryEvent.model_validate` | Además, `properties` contra el catálogo generado desde `event-schemas.json` | Sin ella, `tags` guardaría claves fuera del allowlist |
| Inmutabilidad | Sin lógica de `UPDATE` ni `DELETE` en el código | Además, un trigger que los rechaza (y `TRUNCATE`) y RLS sin políticas | La garantiza la base, no solo la API |
| Creación de la tabla | "Crea la tabla en Supabase" | Solo con `migrations/002_telemetry_events.sql`; la API no la crea al arrancar | `create_all` la crearía sin índice GIN, trigger ni RLS |
| Fallo de la base | 200 mientras el envelope sea parseable | 503 `telemetry_storage_unavailable` | El backoffice reintenta los 5xx; con 200 el lote se perdería en silencio |
| Lotes límite | — | Más de 100 eventos: 422 `too_many_events`; `events: []`: 200 con ceros | El máximo de la fase de captura se mantiene |
| SQLAlchemy en ejecución | Regla del Hito 5: solo `sqlmodel` | El dominio `telemetry` importa SQLAlchemy (`insert` de cada dialecto, `JSONB`, registro propio) | `sqlmodel` no expone `ON CONFLICT` ni `JSONB` |
| Riesgos R2 y R4 del plan | Plan: anonimizar eventos al borrar una cuenta; guardar la hora de recepción | Sin reescrituras; sin columna de recepción | La tabla es inmutable y tiene ocho columnas |
| Destino del PR | La rama principal (`main`) | `feature/telemetry-capture` | Los PR #17 a #22 siguen abiertos; decisión del desarrollador |
| Tablas del inventario en Supabase | Fuera del enunciado | Migración 003: RLS sin políticas y sin permisos para `anon` ni `authenticated` | Supabase las marcaba como *unrestricted*; decisión del desarrollador hacerlo en esta rama |

### 1. La estructura de la tabla viene de otro documento de la academia

La Fase 1 del enunciado dice "crea la tabla `telemetry_events` con la siguiente estructura" y "mapea cada `TelemetryEvent` con este contrato", pero las dos tablas no aparecen en la página, y los criterios piden "las ocho columnas". El desarrollador las encontró en otro documento de la academia: columnas, tipos, restricciones, índices y un mapeo indicativo que deja las reglas de `service` y `level` "al plan del estudiante". La implementación sigue ese contrato al pie de la letra en nombres, tipos, defaults e índices.

### 2. `service`, `level`, `value` y `message` salen del plan

- **`service`:** de `source` (`browser` → `backoffice`; `api`, `bff` y `process` igual), no una constante. Hoy todo es `backoffice`, pero los eventos de la API llegarán como `api` sin tocar el receptor.
- **`level`:** fijo por tipo de evento: `error` en los fallos (4 eventos), `warn` en los rechazos y alertas que alguien debería mirar (11, entre ellos `direct_stock_edit_rejected` y `stock_threshold_triggered`) e `info` en el resto.
- **`value`:** como mucho una propiedad numérica principal por evento (la cantidad en el inventario, la duración en el rendimiento, el porcentaje en las variaciones de precio). No tiene unidad propia: la da el `event_type`, así que nunca se suma entre tipos.
- **`message`:** una plantilla en español por evento, con huecos que solo pueden usar claves del allowlist, de 200 caracteres como máximo.

Las cuatro reglas viven como anotaciones (`x-level`, `x-value`, `x-message`) en `event-schemas.json` y llegan al receptor por un catálogo generado (`uv run telemetry-catalog`). Una prueba falla si el catálogo se desfasa.

**Coste:** tres anotaciones más por evento que mantener en el esquema.

### 3. El `id` es el `eventId` y los repetidos no se duplican

El contrato deja `id` con `gen_random_uuid()`. El receptor envía el `eventId` del envelope como `id` (el default se conserva para cualquier otra inserción) y el bulk insert lleva `ON CONFLICT (id) DO NOTHING`. Un lote puede llegar dos veces: un reintento tras un timeout cuya respuesta se perdió, o un `sendBeacon` que sale justo después de un `fetch` que sí llegó. Los repetidos cuentan en `stored`, porque ya están guardados, así que `received = stored + rejected` siempre; el log dice cuántos eran repetidos.

**Coste:** ninguno en la operación: sigue siendo una sentencia por lote.

### 4. Cinco campos del envelope van en `tags`

El documento de la academia permite guardar en `tags` los campos del envelope que el plan necesite. Van `session_id`, `user_id`, `request_id`, `schema_version` y `environment`, en snake_case como el resto de las claves y siempre presentes (con `null` si no hay valor). `eventId` y `source` no se repiten, porque ya son `id` y `service`. Una prueba comprueba que ninguna propiedad del catálogo usa esos cinco nombres.

**Coste:** `tags` deja de ser exactamente `properties`; las consultas por dimensiones de negocio no cambian.

### 5. `properties` también se valida contra el catálogo

`TelemetryEvent` se reutiliza sin cambios (criterio de evaluación), pero solo comprueba que `properties` es un objeto. Para que `tags` "preserve los allowlists", el receptor comprueba además cada evento contra el catálogo generado desde `event-schemas.json`, con la misma regla que `track()` en el backoffice: tipo conocido, propiedades obligatorias presentes y ninguna clave fuera del allowlist. También rechaza los valores que PostgreSQL no puede guardar en JSONB (NaN, infinitos, el carácter NUL): sin ese filtro, un solo valor así haría fallar el INSERT del lote entero.

**Coste:** un evento con una clave nueva se rechaza hasta que el esquema la incluya y se regenere el catálogo. Es el comportamiento buscado.

### 6. La base garantiza la inmutabilidad

El criterio pide que no haya lógica de `UPDATE` ni `DELETE`: el dominio solo inserta, y una prueba lo comprueba. Además, la migración crea un trigger que rechaza `UPDATE`, `DELETE` y `TRUNCATE` venga de donde venga (la consola de Supabase, un script), y activa RLS sin políticas con los permisos de `anon` y `authenticated` retirados: Supabase publica las tablas de `public` en su API REST, y sin esto cualquiera con la clave `anon` podría leer o escribir eventos. La API se conecta como `postgres`, que no está sujeto a RLS.

**Coste:** una purga excepcional (retención, derecho de supresión) exige desactivar el trigger a mano en una transacción; la migración documenta cómo.

### 7. La tabla la crea solo la migración

La API crea las tablas del inventario al arrancar con `create_all`. Si el modelo de telemetría estuviera en ese `metadata`, una API arrancada antes de ejecutar la migración crearía `telemetry_events` sin índice GIN, sin trigger y sin RLS. Por eso `TelemetryEventRow` tiene un registro propio y la tabla solo la crea `migrations/002_telemetry_events.sql`, idempotente, que el desarrollador ejecutó en el SQL Editor. Sin la tabla, el receptor responde 503 y su log pide la migración.

**Coste:** un paso manual al desplegar en una base nueva.

### 8. Un fallo de la base responde 503

El enunciado pide 200 mientras el envelope sea parseable. Eso se cumple para la validación: un lote en el que se rechazan todos los eventos sigue respondiendo 200. Pero si la base no puede guardar (caída, o falta la tabla), el receptor responde 503 `telemetry_storage_unavailable` y no guarda nada. El `TelemetryService` reintenta los 5xx con su backoff, y el `ON CONFLICT` hace seguros los reintentos. Con un 200, el backoffice daría el lote por entregado y se perdería en silencio.

**Coste:** ninguno para el frontend, que ya trataba los 5xx así.

### 9. Lotes límite

Más de 100 eventos responden 422 `too_many_events` (el máximo de la fase de captura se mantiene, con su propio código: un cliente con un fallo no puede inundar la tabla sin que se note). `events: []` responde 200 con ceros sin tocar la base. Las claves junto a `events` se ignoran, como pide la lectura laxa. Un elemento que no es un objeto cuenta en `rejected`.

### 10. SQLAlchemy en el dominio de telemetría

El Hito 5 fijó que la API solo use `sqlmodel` en ejecución. `sqlmodel` exporta un `insert` genérico, pero `ON CONFLICT DO NOTHING` solo existe en el `insert` de cada dialecto (`sqlalchemy.dialects.postgresql` en Supabase, `sqlalchemy.dialects.sqlite` en las pruebas), y `JSONB` también viene del dialecto. La excepción se limita al dominio `telemetry`; el inventario sigue igual.

**Coste:** el dominio depende de la API de SQLAlchemy además de la de SQLModel.

### 11. R2 y R4 del plan se ajustan

El plan prometía poner `userId` a `null` en los eventos de una cuenta borrada (R2) y guardar la hora de recepción (R4). La primera sería un `UPDATE` sobre una tabla inmutable; la segunda, una novena columna. Ahora los eventos no se reescriben (al borrar la cuenta, su UUID deja de corresponder a nadie; si una solicitud de supresión obliga a borrarlos, se usa la purga manual) y la hora de recepción queda en el log `api.telemetry`.

### 12. Pull Request contra la rama anterior

El enunciado pide el PR contra la rama principal. La rama sale de `feature/telemetry-capture` y el PR apunta a ella, porque los PR #17 a #22 siguen abiertos; lo decidió el desarrollador. El título es `feat: telemetry event storage`.

### 13. RLS en las tablas del inventario (migración 003)

Al crear `telemetry_events`, el Table Editor de Supabase mostró las tres tablas del inventario (Hito 5) como *unrestricted*: sin RLS, cualquiera con la URL del proyecto y la clave `anon` podía leerlas y modificarlas por la API REST de Supabase, saltándose la autenticación de la API de Brasaland y la regla de que el stock solo cambia con órdenes. No lo pide el enunciado, pero el desarrollador decidió corregirlo al final de esta rama. `migrations/003_inventory_rls.sql` hace con ellas lo mismo que la 002 con `telemetry_events` (RLS sin políticas y sin permisos para `anon` ni `authenticated`, también en sus secuencias). Ningún componente del proyecto usa esa API REST, y la API de Brasaland se conecta como `postgres`, que no está sujeto a RLS. `tests/core/test_migrations.py` falla si una tabla de la API queda sin RLS.

**Coste:** volver a ejecutar la 003 si las tablas se recrean en una base nueva, porque la API las crea al arrancar con `create_all`.

### Verificación de los criterios

| Criterio | Cumplimiento | Evidencia |
| --- | --- | --- |
| `telemetry_events` existe en Supabase con las ocho columnas, los tres índices y sin lógica de UPDATE/DELETE | ✅ | `migrations/002_telemetry_events.sql`, ejecutada en Supabase; probada en PostgreSQL 17 (trigger, RLS e idempotencia); `tests/telemetry/test_telemetry_models.py` |
| El endpoint hace bulk insert y devuelve `{ "received", "stored", "rejected" }` | ✅ | `app/domains/telemetry/service.py` (`store_events`) y `router.py`; `tests/integration/test_telemetry_router.py` |
| Los inválidos se rechazan uno a uno sin cancelar el lote, con `model_validate` y sin body tipado | ✅ | `TelemetryBatch.events: list[Any]` y `parse_batch`; con curl contra Supabase, `{"received":7,"stored":2,"rejected":5}` |
| `TelemetryEvent` no se modificó | ✅ | Su clase es idéntica a la de `84772fe` (comparada por árbol sintáctico) |
| El frontend no cambió ni una línea | ✅ | `git diff feature/telemetry-capture -- uis/` vacío |
| Los eventos aparecen con `event_type`, `timestamp` y `tags` poblados, técnicos y de negocio | ✅ | Captura de `telemetry_events` en Supabase: `inbound_order_created`, `stock_waste_registered`, `direct_stock_edit_rejected`, `login_failed`, `page_viewed`, `api_latency_recorded`… |
| `tags` preserva los allowlists y las dimensiones del briefing | ✅ | Validación contra el catálogo; en Supabase, `inbound_order_created` con `location_id`, `country`, `product_id`, `product_category`, `quantity`, `unit`, `currency`, `supplier_id` y `unit_cost` |
| Un solo INSERT por lote | ✅ | `INSERT … VALUES (…), (…) ON CONFLICT (id) DO NOTHING`; `test_writes_the_whole_batch_with_a_single_insert` cuenta las sentencias |

## Reporte técnico de telemetría

Tercera implementación del plan de telemetría, en la rama `feature/telemetry-report`. Los eventos de `telemetry_events` se transforman en un reporte técnico (volumen, fallos, latencia de la API y fallos de login, por día UTC) que sirve `GET /telemetry/report`. Coincide con el enunciado en lo siguiente:

- **Pipeline:** `services/telemetry/analysis.py`, en la ruta literal, con cuatro funciones de métrica independientes y sin efectos secundarios. Cada una sigue `cargar (SQL) → refinar → convertir tipos → agrupar → agregar`, convierte `timestamp` con `pd.to_datetime(..., utc=True)` antes de agrupar, no usa bucles y devuelve una lista de dicts.
- **Filtros:** la ventana (inicio inclusivo, fin exclusivo, en UTC) y los `event_type` se aplican en SQL, con `IN (...)` en la métrica de login; las dimensiones de `tags` y las tasas se calculan en Pandas.
- **Endpoint:** `start_date` y `end_date` opcionales en ISO 8601, los últimos 7 días por defecto, el período resuelto una sola vez y pasado a cada función, y la respuesta `{"period": {"from", "to"}, "metrics": {...}}` con `events_per_day` y `error_rate_by_type`.
- **Cache:** en memoria con TTL de 60 s; la misma combinación de fechas dentro del TTL no recalcula.
- **Actividades adicionales:** las dos. `auth_failure_rate` está en el reporte y el backoffice tiene una vista técnica que muestra el período y una visualización por métrica.

Las decisiones (R1 a R6) se tomaron con el desarrollador el 20 de noviembre de 2026. El plan (`docs/telemetry/telemetry-plan.md`, sección 16) se actualizó con ellas antes de escribir código.

> **Estado:** completado y verificado contra Supabase con datos reales de dos días (2026-11-19 y 2026-11-20), un commit por fase, hechos por el desarrollador.

| Qué | Briefing o enunciado | Implementación | Motivo principal |
| --- | --- | --- | --- |
| Eventos de login | `user_login_failed` y `user_login_succeeded` | `login_failed` y `login_succeeded` | Son los nombres del catálogo aprobado y de los eventos ya guardados |
| Ubicación de `analysis.py` | `services/telemetry/analysis.py` | En esa ruta, como paquete local `brasaland-telemetry` instalado en la API en modo editable | La API vive en `services/brasaland-api`; así la ruta es la literal y la API lo importa sin rutas relativas |
| Acceso al endpoint | Sin especificar | Token y rol `admin` (401 sin token, 403 con otro rol) | El reporte expone rutas, errores y latencias internas |
| Validación del período | Sin especificar | 422 con fecha mal formada, `invalid_period` y `period_too_long` (más de 90 días) | Un período al revés o enorme no debe llegar a la base |
| Fallo de la base | Sin especificar | 503 `telemetry_report_unavailable`, sin guardar en cache | Un reporte vacío por un fallo parecería un sistema sin actividad |
| Latencia por ruta | Ejemplo orientativo | Agrupada por día, método y ruta, con media ponderada por `1/sample_rate` | `GET` y `POST` de una ruta no se comparan; el muestreo sesgaría la media |
| Ruta del dashboard | "ej. `/telemetry`" | `/telemetria` | Las rutas del backoffice están en español |
| Acceso del dashboard a la API | Sin especificar | Ruta propia del intermediario: `app/api/telemetry/report/route.ts` | El intermediario solo llegaba a `/api/v1`, y el reporte está fuera |
| Gráficos | "Cualquier librería disponible" o una tabla | Barras con `div` y Tailwind, y tablas | El backoffice no tiene librería de gráficos y su stack es solo Tailwind, TS, React y Next |
| Destino del PR | Oculto en la captura | `feature/telemetry-storage` | Los PR #17 a #23 siguen abiertos; decisión del desarrollador |

### 1. Los eventos de login se llaman `login_failed` y `login_succeeded`

La actividad adicional nombra `user_login_failed` y `user_login_succeeded`. En el catálogo aprobado (`docs/telemetry/telemetry-plan.md`, §5, y `event-schemas.json`) son `login_failed` y `login_succeeded`, y con esos nombres están guardados en Supabase. Renombrarlos ahora rompería la continuidad de la tabla, que es inmutable. La métrica sigue la consigna al pie de la letra: carga los dos tipos con `event_type IN (...)` en SQL y calcula `failed / attempts` por día en Pandas.

**Coste:** ninguno; la clave del reporte es la del enunciado, `auth_failure_rate`.

### 2. `services/telemetry` es un paquete local

El enunciado pide `analysis.py` en `services/telemetry/`, pero la API está en `services/brasaland-api/`. Para respetar la ruta literal sin manipular `sys.path`, `services/telemetry/` es un paquete (`brasaland-telemetry`) que la API declara como dependencia local y uv instala en modo editable, igual que `packages/shared`. El endpoint vive en el dominio `telemetry` de la API, que importa las funciones del paquete. `requirements.txt` lo excluye (`--no-emit-package`), el Dockerfile lo copia e instala antes que la API, y `docker-compose.yml` lo monta para que los cambios se vean sin reconstruir la imagen.

**Coste:** un `pyproject.toml` más y un paso más en el Dockerfile.

### 3. El reporte es solo para administradores

El enunciado no dice quién puede ver el reporte. Expone las rutas internas de la API, sus latencias y los tipos de fallo, así que exige token y rol `admin`, como el resto de las operaciones sensibles. El dashboard es visible en el menú para todos, pero quien no es administrador ve "Solo los administradores pueden ver el reporte técnico." en lugar de los datos, y su sesión no se cierra.

### 4. Validación del período y fallo de la base

Además del formato ISO 8601 (fecha sola = 00:00 UTC; sin zona = UTC), el endpoint responde 422 `invalid_period` si el inicio no es anterior al fin y `period_too_long` por encima de 90 días: el reporte es un radar operacional, y un período mayor cargaría en memoria muchas más filas sin responder mejor ninguna pregunta. Si la base falla o falta la tabla, responde 503 `telemetry_report_unavailable` y no guarda nada en cache. Un reporte con ceros parecería un sistema sin actividad.

**Coste:** un período de más de 90 días exige varias peticiones.

### 5. La latencia se agrupa también por método y se pondera por el muestreo

La primera versión del plan (R2) agrupaba la latencia por día y ruta. En la Fase 1 se añadió el método, porque `GET` y `POST` de una misma ruta tienen latencias muy distintas y mezclarlos daría una media sin significado. Además, `api_latency_recorded` es un muestreo: guarda siempre las peticiones lentas y las de error, y 1 de cada 10 del resto (`sample_rate` en `tags`). La media se pondera por `1/sample_rate` con operaciones de Pandas, para que el muestreo no la sesgue hacia las lentas; `samples` es el número de eventos y `max_ms` no se pondera.

### 6. El dashboard está en `/telemetria` y llega a la API por su propia ruta

El enunciado sugiere `/telemetry`. Las rutas del backoffice están en español (`/inventario`, `/proveedores`, `/incidencias`), así que la vista está en `/telemetria`, con el título "Telemetría técnica" en la sección "Herramientas".

El navegador nunca llama a la API directamente: pasa por el intermediario (BFF), que solo reenviaba a `/api/v1`. El reporte está fuera de ese prefijo, como el receptor de eventos, así que tiene su propia ruta, `app/api/telemetry/report/route.ts`, que toma el origen de `API_BASE_URL`. La lógica de reenvío se extrajo a `lib/bff/proxy.ts` y la comparten el catch-all y la ruta nueva, sin cambiar el comportamiento del primero. Por la misma razón, la latencia de esta llamada se registra como `/telemetry/report`, sin el prefijo `/api/v1`.

En la vista, las dos fechas del filtro se incluyen; el fin se envía a la API como el día siguiente, porque la API lo toma como exclusivo.

**Coste:** una ruta más en el intermediario.

### 7. Sin librería de gráficos

El enunciado permite cualquier librería disponible o una tabla HTML. El backoffice no tiene ninguna, y su stack es solo Tailwind, TypeScript, React y Next. `events_per_day` se muestra como una barra por día apilada por nivel, hecha con `div` y Tailwind; las otras tres métricas, como tablas. La vista solo muestra las métricas del reporte, nada de negocio.

### 8. Pull Request contra la rama anterior

La rama sale de `feature/telemetry-storage` y el PR apunta a ella, porque los PR #17 a #23 siguen abiertos; lo decidió el desarrollador. El título es `feat: telemetry report endpoint`.

### Verificación de los criterios

| Criterio | Cumplimiento | Evidencia |
| --- | --- | --- |
| `services/telemetry/analysis.py` existe con al menos tres funciones de métrica independientes | ✅ | Cuatro: `events_per_day`, `error_rate_by_type`, `api_latency_by_route` y `auth_failure_rate`; `tests/telemetry/test_report_analysis.py` comprueba que dos llamadas iguales dan el mismo resultado |
| Cada función sigue `cargar → refinar → convertir tipos → agrupar → agregar` | ✅ | El SQL filtra por ventana y `event_type`; el resto en Pandas, en ese orden (`analysis.py`) |
| Timestamps a `datetime` con `utc=True` antes de cualquier `groupby` temporal | ✅ | `pd.to_datetime(frame["timestamp"], utc=True, format="ISO8601")` en `_to_utc_day`, antes de cada agrupación; una prueba con eventos en el límite del día UTC |
| Sin bucles para calcular métricas | ✅ | Solo `groupby`, `agg`, `size`, `unstack`, `reindex` y operaciones vectoriales; `test_the_pipeline_has_no_loops` recorre el árbol sintáctico y falla con cualquier bucle, comprensión o `apply` |
| Cada función devuelve una lista de dicts serializable a JSON | ✅ | `to_dict(orient="records")`; una prueba comprueba tipos nativos y pasa cada resultado por `json.dumps` |
| `GET /telemetry/report` acepta `start_date` y `end_date` opcionales, 7 días por defecto | ✅ | `app/domains/telemetry/report.py` (`resolve_period`); `tests/telemetry/test_report_period.py` |
| JSON con `{ "period": {...}, "metrics": {...} }` | ✅ | Con curl contra Supabase el 2026-11-20 (muestra en la descripción del PR) |
| Cache en memoria con TTL de 60 s | ✅ | `TTLCache(60)`; segunda petición igual con `X-Cache: HIT`; `tests/integration/test_telemetry_report_router.py` |
| Cada métrica responde una pregunta técnica u operacional | ✅ | Volumen, fallos, latencia y login (tabla de §16.2 del plan); ninguna métrica de negocio |
| Las métricas tienen una dimensión de agrupamiento | ✅ | Todas por día UTC, y además por nivel, tipo de evento o método y ruta |
| Datos reales con dimensión temporal | ✅ | 53 eventos de dos días; los totales por día y nivel, las tasas y los intentos de login coinciden con un `GROUP BY` independiente en SQL |

---

## Pipeline de desempeño de negocio

Diseño (Parte 1 de 3) del pipeline que produce el "Reporte Semanal de Costo y Merma por Local", en la rama `feature/pipeline-design`. El entregable es `data/pipelines/PIPELINE_DESIGN.md`; la implementación con Prefect llega en las Partes 2 y 3. Coincide con el briefing y el enunciado en lo siguiente:

- **Entregable y KPIs:** el propósito nombra el reporte, su audiencia (Mariana y Felipe), su frecuencia (fresco el lunes por la mañana) y los cinco KPIs con sus columnas (`total_purchase_cost`, `total_waste_cost`, `waste_ratio`, `stockout_events_count` y `price_alert_events_count`).
- **Fuente:** `telemetry_events` en solo lectura, filtrada a los eventos obligatorios del briefing. `services/telemetry/analysis.py` y `GET /telemetry/report` no cambian.
- **Destino:** `reporting.weekly_location_performance` con el DDL literal del briefing; el upsert se apoya en su `unique (location_id, week_start)`.
- **Agregación:** una fila por local y semana ISO, con `week_start` en UTC, la moneda del local y sin convertir monedas.
- **Endpoints:** las tres rutas literales del briefing en el módulo nuevo `services/reporting/`, separado de `services/telemetry/`.
- **Coste en los eventos:** `inbound_order_created` ya tenía `unit_cost`; `stock_waste_registered` lo añade como campo aditivo (versión 1.1.0), como permite el enunciado.

Las decisiones (P1 a P6) se tomaron con el desarrollador el 20 de noviembre de 2026; el ajuste de P5, el 23. Están en la sección 9 del documento de diseño.

> **Estado:** diseño completo. Un commit por fase, hechos por el desarrollador: Fase 0 (catálogo de locales, `7658a09` a `d929b00`), Fase 1 (coste de la merma, `d5c4824`) y Fase 2 (documento, `5db3b2b`).

| Qué | Briefing o enunciado | Implementación | Motivo principal |
| --- | --- | --- | --- |
| Formato de `location_id` | Ejemplo `"medellin-centro"`, con guion | `medellin_centro`, con guion bajo | Es el `code` del catálogo `locations`, el `branch` del briefing del gestor de incidencias |
| Nombre del local en la respuesta | No aparece | `location_name` en cada local de `GET /reporting/weekly-location-performance` | Mariana lee "Miami Hialeah", no un código |
| Catálogo de locales | No lo menciona | Tabla `locations` (migración 004), validación del país en el inventario y local primero en el backoffice | `location_id` era un entero sin sede ni país; sin catálogo no hay `country` fiable por local |
| Coste de una merma sin `unit_cost` | Suma de los costes de la semana | Cuenta con coste 0 y se registra en el log | Las mermas 1.0.0 no traen coste, y no se inventa |
| Alertas de precio | "subió de forma anómala" | Solo `variance_pct > 0`; las bajadas se descartan y se cuentan en el log | El evento se emite con subidas y con bajadas |
| Quiebre de stock | "cayó por debajo del mínimo configurado" en un local | Umbral provisional por unidad sobre el stock global (brecha B3) | No existen mínimos ni stock por local |
| `outbound_order_created` | En la tabla de fuentes, como contexto | No se extrae en la v1 | No alimenta ningún KPI ni ninguna columna |
| Entorno de los eventos | Sin especificar | Solo `environment = production`, configurable | Riesgo R7 del plan de telemetría: los datos de prueba no entran en los indicadores |
| Locales sin actividad | Sin especificar | Una fila con ceros para cada uno de los 14 locales y cada semana | Una semana sin actividad debe distinguirse de una semana sin calcular |
| Ventana de cada corrida | Sin especificar | Las 4 últimas semanas cerradas, recalculadas con upsert; backfill por rango | Absorbe los eventos que llegan tarde sin marca de agua (R4) |
| Hora de la corrida | "fresco la mañana del lunes" | Lunes a las 06:00 America/Bogota (11:00 UTC) | La semana cierra el lunes a las 00:00 UTC |
| Log de corridas | "estado y metadata de la última corrida" | Tabla `reporting.pipeline_runs` con 18 campos | El enunciado pide un log auditable con al menos cinco campos |
| Lectura de `reporting.*` | El enunciado pide que los endpoints importen de `data/pipelines/` | El SQL de lectura y el disparo viven en `data/pipelines/`; `services/reporting/` solo hace HTTP | Ninguna lógica de datos en `services/` |
| Acceso a los endpoints | Sin especificar | Lecturas para `admin` y `manager`; disparo solo `admin` | Los gerentes leen el reporte; reprocesar es una operación de administración |
| Credenciales del pipeline | "por ejemplo, la conexión a Supabase" | Rol `reporting_pipeline` en un bloque `Secret` | La base garantiza la solo lectura sobre `telemetry_events` |
| Destino del PR | Sin especificar | `feature/telemetry-report` | Los PR #17 a #24 siguen abiertos |

### 1. `location_id` usa el código con guion bajo

El ejemplo del briefing (§6) muestra `"location_id": "medellin-centro"`. La tabla de destino guarda el `code` del catálogo `locations`, que reproduce los `branch` del briefing del gestor de incidencias (`medellin_centro`… `fort_lauderdale`), con guion bajo. Usar el guion obligaría a mantener dos códigos para el mismo local, y el gestor ya guarda incidencias con el guion bajo. El tipo (`text`) y el significado son los del briefing; solo cambia el separador.

**Coste:** quien compare con el ejemplo verá otro separador.

### 2. La respuesta de KPIs añade `location_name`

`GET /reporting/weekly-location-performance` devuelve cada local con la forma del briefing, más `location_name` ("Medellín Centro", de `locations.name`). Es un campo aditivo: los demás no cambian de nombre ni de tipo, y la tabla de destino queda exacta. El dashboard de la Parte 3 lo muestra sin otra llamada.

### 3. Catálogo de locales y su restricción en el inventario (Fase 0)

El briefing da por hecho que cada local tiene un `country` y una `currency`. Hasta esta tarea, `location_id` era un entero de 1 a 14 sin sede, y el país de cada evento salía del ingrediente (brecha B7): un mismo local podía aparecer con dos países. Antes del diseño se añadió:

- la tabla `locations` con las 14 sedes (migración 004) y `GET /api/v1/locations`;
- el 422 `location_country_mismatch` en entradas y salidas cuando el ingrediente es de otro país que el local;
- en el backoffice, el local primero en los formularios del inventario, con solo los ingredientes de su país;
- `country` y `currency` del local en los eventos del inventario.

Las 3 órdenes de prueba que incumplían la regla se conservan (las tablas del inventario no se reescriben). El local asignado a cada cuenta (brecha B10) queda para una tarea propia.

**Coste:** trabajo fuera del documento de diseño, en cuatro commits propios.

### 4. Las mermas sin coste cuentan con coste 0

El briefing calcula `total_waste_cost` como la suma de los costes de las mermas. `stock_waste_registered` 1.1.0 lleva `unit_cost`, que el backoffice calcula como el coste medio ponderado de las entradas del producto (plan de telemetría, §17). Las mermas 1.0.0, y las de productos sin entradas con coste, no lo traen: cuentan con coste 0, y el log de la corrida dice cuántas hubo (`waste_events_without_cost`).

**Coste:** el KPI puede quedar por debajo del real, y la corrida lo indica.

### 5. Solo cuentan las alertas de subida

El briefing define la frecuencia de alertas de precio como las veces que el coste "subió de forma anómala". `ingredient_price_variance_detected` se emite con desviaciones de más del 10 % en los dos sentidos (plan de telemetría, §3.2). La transformación cuenta solo `variance_pct > 0` y descarta las bajadas con el motivo `price_decrease` en el log. La captura no cambia, y las bajadas siguen disponibles para otros usos.

### 6. El quiebre de stock usa el umbral provisional

El briefing cuenta las veces que el stock de un ingrediente "en un local" cayó por debajo del "mínimo configurado". No existen mínimos por local ni stock por local (brecha B3, decisión D7 del Hito 5): `stock_threshold_triggered` se emite cuando el stock global del producto cruza el umbral de stock bajo de su unidad (40 kg, 25 litros o 100 unidades), y se asigna al local de la salida que provocó el cruce. El pipeline lo cuenta tal como llega y el diseño documenta la limitación (§8). Los mínimos y el stock por local son una tarea propia; al cerrarla, la versión del evento subirá para distinguir las semanas medidas con cada criterio.

**Coste:** `stockout_events_count` es una aproximación hasta entonces.

### 7. `outbound_order_created` no se extrae

El briefing lo incluye en la tabla de fuentes "solo como volumen operativo". No alimenta ningún KPI ni ninguna columna de `weekly_location_performance`, y el enunciado pide cuestionar toda etapa que no sostenga el entregable. Si la Parte 3 necesita detectar anomalías de volumen, se añade entonces.

### 8. Solo los eventos de `production`

El briefing no habla de entornos. Cada evento lleva `environment` en `tags`, y el plan de telemetría (riesgo R7) reserva los indicadores de negocio para `production`. El entorno vive en el bloque de configuración del pipeline: en desarrollo se apunta a `development` para verificarlo.

**Coste:** con los datos actuales (todos de `development`), el reporte de producción saldría en ceros.

### 9. Ventana, filas con ceros y hora de la corrida

- **Ventana.** Cada corrida recalcula enteras las 4 últimas semanas ISO cerradas y hace upsert. La tabla de telemetría no guarda la hora de recepción (riesgo R4), así que no hay una marca de agua fiable para leer solo lo nuevo; recalcular absorbe los eventos que llegan tarde. Un backfill por rango (`POST /reporting/pipeline-runs`) cubre los retrasos mayores y los reprocesos.
- **Ceros.** Cada corrida escribe una fila por cada uno de los 14 locales y cada semana, también sin actividad, para que la falta de una fila signifique "sin calcular".
- **Hora.** Lunes a las 06:00 America/Bogota (11:00 UTC), con la semana ya cerrada a las 00:00 UTC. Un evento del domingo a partir de las 19:00 en Bogotá cae en la semana siguiente, porque el briefing fija la semana en UTC.

### 10. Log de corridas en `reporting.pipeline_runs`

El briefing pide "estado y metadata de la última corrida" y el enunciado, un log con al menos cinco campos justificados. La tabla tiene 18 campos (§4.4 del diseño), incluidos los conteos de eventos rechazados y descartados por motivo, y una columna `pipeline` para reutilizarla con otros pipelines. Un índice único parcial impide dos corridas activas del mismo pipeline. La crea la misma migración que la tabla de destino (`005_reporting.sql`).

### 11. La lectura y el disparo viven en `data/pipelines/`

El enunciado pide que cada endpoint importe una función o un flow de `data/pipelines/`, y que ninguna lógica de ETL viva en `services/`. La primera versión de P5 dejaba la lectura de `reporting.*` en `services/reporting/`; el 23 de noviembre se ajustó: `repository.py` (lecturas y upsert) y `trigger.py` (disparo con `run_deployment`) están en el paquete del pipeline, dueño de sus tablas, y `services/reporting/` solo autentica, valida y serializa. Las transformaciones reutilizables van en `data/process/`, como indica el enunciado.

### 12. Acceso y credenciales

- **Endpoints.** El briefing no dice quién puede usarlos. Las dos lecturas son para `admin` y `manager` (el reporte es para la dirección y los gerentes de operación); el disparo manual, solo para `admin`, porque reescribe semanas ya publicadas.
- **Credenciales.** La conexión del pipeline usa un rol propio de Supabase, `reporting_pipeline`, con `SELECT` sobre `telemetry_events` y `locations` y escritura solo en `reporting.*`. Su cadena de conexión vive en un bloque `Secret` de Prefect. Así, la base garantiza que el pipeline nunca escribe en `telemetry_events`.

**Coste:** el desarrollador crea el rol en Supabase antes de la Parte 2.

### 13. Pull Request contra la rama anterior

La rama sale de `feature/telemetry-report`, y el PR apunta a ella porque los PR #17 a #24 siguen abiertos. El commit del documento lleva el mensaje del enunciado, `feat: add business performance pipeline design document`.

### Verificación de los criterios

| Criterio | Cumplimiento | Evidencia |
| --- | --- | --- |
| `data/pipelines/PIPELINE_DESIGN.md` existe en Markdown legible | ✅ | Commit `5db3b2b`, con índice y nueve secciones |
| Estado actual y brecha de negocio | ✅ | §2: eventos capturados, `telemetry_events` y `locations`, el reporte técnico y lo que no responde (§2.4) |
| Formato de extracción (tablas, payload, cadencia) | ✅ | §3.1: las dos fuentes, la consulta SQL, un `tags` de ejemplo y la frecuencia de llegada de los eventos |
| Propósito en una frase con el entregable y los KPIs | ✅ | §1: el reporte, su audiencia, los cinco KPIs y los cuatro eventos que los alimentan |
| No toca `analysis.py`, `GET /telemetry/report` ni escribe en `telemetry_events` | ✅ | El diseño escribe solo en `reporting.*`, por un rol sin escritura en la fuente (§3.5); la única extensión es `unit_cost` en la merma (plan de telemetría, §17) |
| Diagrama con tres etapas y nombres reales | ✅ | §3.2: Mermaid con extracción, transformación y carga, las tablas y las tasks |
| Estrategia para registros que cambian | ✅ | §3.4: recálculo de la ventana, upsert por `(location_id, week_start)` con el SQL, y deduplicación por `order_id` |
| Idempotencia tras un fallo en la carga | ✅ | §4.1: carga en una transacción y una tabla con el estado de las dos tablas en cada momento de la segunda corrida |
| Log con al menos cinco campos con nombre, tipo y justificación | ✅ | §4.4: 18 campos |
| Un flow y al menos tres tasks con nombres concretos | ✅ | §5: `weekly_location_performance_flow` y 7 tasks, con states, hooks, deployment y bloques |
| Tres endpoints en `services/reporting/` con su función de `data/pipelines/` | ✅ | §6: `read_weekly_location_performance`, `read_latest_pipeline_run` y `trigger_pipeline_run` |
| Coherente con los eventos y las métricas obligatorias del briefing | ✅ | Los nombres de eventos, propiedades, columnas y locales son los del catálogo de telemetría y del briefing |

---

## Pipeline de desempeño de negocio resiliente

Implementación (Parte 2 de 3) del pipeline diseñado en la sección anterior, en la rama `feature/pipeline-implementation`. Los entregables son `data/pipelines/pipeline.py` (un flow de Prefect con 9 tasks) y los tres endpoints de `services/reporting/`. Coincide con el briefing y el enunciado en lo siguiente:

- **Punto de entrada:** `data/pipelines/pipeline.py` define el flow `weekly_location_performance_flow` y se ejecuta con `python data/pipelines/pipeline.py`.
- **Carpetas:** transformaciones reutilizables en `data/process/`, extracción de cada corrida en `data/raw/` y comprobaciones de la corrida en `data/eval/`.
- **Fuente y destino:** lee `telemetry_events` y `locations` con un rol sin permisos de escritura sobre ellas, y escribe en `reporting.weekly_location_performance` (DDL literal del briefing) con un upsert sobre su `unique (location_id, week_start)`. `services/telemetry/analysis.py` y `GET /telemetry/report` no cambian.
- **KPIs:** los cinco del briefing, con sus nombres de columna, comparados con un cálculo independiente en SQL.
- **Resiliencia:** reintentos justificados en las tasks que hablan con la base, dos pasos opcionales con `return_state=True`, la carga con `return_state=True` y tratada en el flow, y caché con `cache_key_fn` y `cache_expiration` en la transformación.
- **Log:** cada corrida queda en `reporting.pipeline_runs` (18 campos, entre ellos inicio, fin, eventos leídos, filas escritas, estado y error).
- **Endpoints:** las tres rutas del briefing en `services/reporting/`, separado de `services/telemetry/`, con la autenticación y el formato de errores de la API, importando de `data/pipelines/`.

Las decisiones (I0 a I5) se tomaron con el desarrollador el 23 de noviembre de 2026. Están, con los ajustes al diseño, en la sección 11 de `data/pipelines/PIPELINE_DESIGN.md`; la frecuencia y los comandos, en su sección 10.

> **Estado:** completa. Un commit por fase, hechos por el desarrollador: Fase 0 (esquema `reporting`, `7839b89`), Fase 1 (transformaciones, `52894b2`), Fase 2 (flow, `39fe52f`), Fase 3 (endpoints, `38fc1b5`), Fase 4 (verificación real, `e1afffa`) y Fase 5 (documentación, con el mensaje del enunciado).

| Qué | Briefing o enunciado | Implementación | Motivo principal |
| --- | --- | --- | --- |
| Instalación de Prefect | `uv add "prefect>=3"` en el entorno | Grupo de dependencias `orchestration` de `data/pipelines/`; la API no lo instala | Importado en la API, Prefect cambia su logging y exige una FastAPI anterior |
| Disparo manual | El endpoint importa flows o funciones de `data/pipelines/` | Importa `trigger.trigger_pipeline_run`, que pone la corrida en la cola de Prefect por su API REST | La API nunca ejecuta el ETL (diseño, §6.3) y no importa Prefect |
| Ejecución programada | Sin especificar | `pipeline.py --serve` en el servicio `reporting-pipeline` de Docker, con `prefect-server` | Deployment de los lunes sin work pool ni worker aparte |
| Corrida sin argumentos | `python data/pipelines/pipeline.py` corre el ETL completo | Lo hace, sobre los eventos de `production`; la verificación usa `--environment development` | Los datos de prueba del backoffice local son de `development` (riesgo R7 del plan de telemetría) |
| Caché | "Si una task ya corrió en la última hora, no se repite" | Caché de 1 hora en la transformación y en el catálogo de locales; no en la extracción de eventos ni en la carga | Releer eventos y reescribir con upsert es lo que hace correcto el resultado |
| Uso de `data/raw/` | Datos de entrada e intermedios | La extracción de cada corrida, sin identificadores de usuario, sesión ni petición, y fuera de Git | La fuente es Supabase; `data/raw/` guarda una copia auditable, no la fuente |
| Log de la corrida | Cinco campos en la base o en un archivo | Tabla `reporting.pipeline_runs`, 18 campos | Ya estaba en el diseño (sección 19, apartado 10) |
| Metadata de la última corrida | Estado, inicio, fin, registros procesados | Todos los campos del log salvo `requested_by` y `prefect_flow_run_id` | Quién pidió la corrida y el id interno de Prefect no son para los lectores del reporte |
| Mensaje del commit | `feat: implement resilient business performance pipeline` | En el último commit; los anteriores, un mensaje por fase | Un commit por fase, como el resto del proyecto |
| Destino del PR | Sin especificar | `feature/pipeline-design` | El PR #25 (diseño) sigue abierto |

### 1. Prefect fuera de la API

El enunciado pide instalar Prefect con `uv add "prefect>=3"`. Está instalado en `data/pipelines/`, en el grupo de dependencias `orchestration`, que `uv sync` instala por defecto. La API depende de `brasaland-pipelines` sin ese grupo por dos motivos comprobados en la Fase 3:

- **Logging.** Importar Prefect configura el logging del proceso: añade un handler al registrador raíz (las líneas de `api.timing` salían duplicadas) y deja el de uvicorn en `WARNING` sin propagación, lo que habría silenciado sus mensajes `INFO`.
- **Versiones.** El paquete de Prefect 3.9 exige `fastapi<0.151`; con él, la API habría bajado de FastAPI 0.162 a 0.150, además de `websockets` y `python-dateutil`.

Una prueba de la API comprueba en un proceso aparte que `app.main` no importa Prefect.

**Coste:** `data/pipelines/` tiene dos dependencias de nivel distinto (el paquete y el grupo), y el servicio `reporting-pipeline` tiene una imagen propia.

### 2. El disparo pone la corrida en la cola, por la API REST de Prefect

El enunciado pide que los endpoints importen flows o funciones de `data/pipelines/` sin duplicar la lógica. `POST /reporting/pipeline-runs` importa `trigger_pipeline_run` de `data/pipelines/trigger.py`, que registra la corrida en `pending` y crea el flow run del deployment `weekly-location-performance/weekly`. El diseño lo hacía con `run_deployment(..., timeout=0)`; `trigger.py` hace las mismas dos llamadas a la API REST de Prefect (`GET /deployments/name/…` y `POST /deployments/{id}/create_flow_run`) con httpx, para no importar Prefect (apartado 1). El flow lo ejecuta el proceso `--serve` del servicio `reporting-pipeline`, nunca el de la API: un reinicio de la API no corta una corrida, y una corrida larga no ocupa la API.

**Coste:** el endpoint necesita `PREFECT_API_URL` y el proceso `--serve` en marcha; sin ellos responde 503 `orchestrator_unavailable`.

### 3. `python data/pipelines/pipeline.py` lee `production`

El enunciado pide que `python data/pipelines/pipeline.py` corra el ETL completo sin errores. Lo hace: abre la corrida, extrae, transforma, carga 56 filas (14 locales × 4 semanas cerradas) y la cierra en `completed`, con código 0. Lee los eventos de `production`, como fija el diseño (sección 19, apartado 8), y hoy todos los eventos de Supabase son de `development`, así que esas filas salen en cero. La verificación con datos reales usa `--environment development --include-current-week`; sus resultados están en la sección 11 del diseño.

El comando necesita el entorno de `data/pipelines/` (`uv sync`) y `REPORTING_DATABASE_URL` en `data/pipelines/.env`. Sin `PREFECT_API_URL`, Prefect arranca un servidor temporal para la corrida; en Windows, ese servidor escribe en la consola errores internos de su SQLite (`UNIQUE constraint failed: task_run_state`), que no afectan a la corrida. Con el servidor de Docker (`PREFECT_API_URL=http://localhost:4200/api`) no aparecen.

**Coste:** con los datos actuales, la corrida por defecto produce ceros.

### 4. Qué se guarda en caché

El enunciado pide que una task que ya corrió con éxito en la última hora no se repita. La caché, de 1 hora, está en las dos tasks cuyo resultado se puede reutilizar sin riesgo:

- **`transform_weekly_location_performance`**, la etapa costosa: la clave incluye los `id` de los eventos, las semanas, el catálogo y la versión de la transformación, así que un evento nuevo o tardío invalida la caché.
- **`extract_locations`**: el catálogo solo cambia con una migración.

La extracción de eventos no se cachea, porque los eventos llegan en cualquier momento y una corrida debe verlos. Tampoco la carga: reescribir con upsert es lo que garantiza la idempotencia. Ni el control de la corrida ni los pasos opcionales, que escriben un archivo por corrida.

**Coste:** cada proceso tiene su caché (el almacenamiento de resultados de Prefect); una corrida desde el host no reutiliza la del contenedor.

### 5. Qué guarda `data/raw/`

El enunciado reserva `data/raw/` para datos de entrada y archivos intermedios. La entrada del pipeline es `telemetry_events`, en Supabase: `data/raw/` no la sustituye. La task opcional `save_raw_extract` guarda la extracción de cada corrida en `data/raw/telemetry_events/<run_id>.json`, sin `user_id`, `session_id` ni `request_id` (plan de telemetría, §8). La carpeta queda fuera de Git y los datos fuente existentes (`incidents-brasaland.csv`) no se tocan. `data/eval/weekly_location_performance/` sigue el mismo criterio para las comprobaciones de cada corrida.

### 6. La metadata de la última corrida no expone quién la pidió

`GET /reporting/pipeline-runs/latest` devuelve el estado, las horas de inicio y fin, los eventos leídos, rechazados y descartados, las filas escritas y el error, como pide el enunciado. No devuelve `requested_by` (el usuario que pidió la corrida manual) ni `prefect_flow_run_id`: los dos quedan en la tabla para la auditoría y para enlazar con Prefect.

### 7. Commits por fase y destino del PR

El enunciado pide un commit con el mensaje `feat: implement resilient business performance pipeline`. Como en el resto del proyecto, el trabajo va en un commit por fase, con un mensaje propio cada uno, y el de la Fase 5 lleva el mensaje del enunciado. La rama sale de `feature/pipeline-design`, y el PR apunta a ella porque el PR #25 sigue abierto.

### Verificación de los criterios

| Criterio | Cumplimiento | Evidencia |
| --- | --- | --- |
| `data/pipelines/pipeline.py` define un flow con tres o más tasks | ✅ | `weekly_location_performance_flow` y 9 tasks (diseño, §5.2) |
| Una task con `retries` mayor que cero y un comentario que lo justifica | ✅ | Control (2), extracción (3) y carga (2), cada una con su comentario; solo ante fallos transitorios. Comprobado con la base inaccesible durante 15 s |
| Una task opcional con `return_state=True`, y el flow continúa si falla | ✅ | `save_raw_extract` y `export_eval_snapshot`. Con `data/raw/telemetry_events/` sin poder escribirse, la corrida terminó en `completed` con `save_raw_extract_failed` |
| Una task de transformación con `cache_key_fn` y `cache_expiration` | ✅ | `transform_weekly_location_performance`, 1 hora, con la clave explicada en un comentario. La segunda corrida la reutilizó (`Cached`) |
| Carga idempotente | ✅ | Upsert sobre `unique (location_id, week_start)` en una transacción. Dos corridas seguidas dejaron los mismos `id` y valores |
| Cinco campos de metadata por corrida | ✅ | `reporting.pipeline_runs`: `started_at`, `finished_at`, `events_read` y `rows_written`, `status`, `failed_task` y `error_message`, entre 18 |
| `python data/pipelines/pipeline.py` corre el ETL completo | ✅ | Corrida de `production` completada con 56 filas y código 0 (apartado 3) |
| Comando de ejecución documentado | ✅ | `PIPELINE_DESIGN.md`, §10, y el docstring de `pipeline.py` |
| Escribe en la tabla del briefing; `telemetry_events` y `analysis.py` intactos | ✅ | Solo escribe en `reporting.*`, con un rol sin escritura en `telemetry_events` (comprobado con `has_table_privilege`) |
| Endpoint con la metadata de la última corrida | ✅ | `GET /reporting/pipeline-runs/latest` |
| Endpoint que dispara una corrida importando de `data/pipelines/` | ✅ | `POST /reporting/pipeline-runs` → `trigger_pipeline_run`; 202, y la corrida la ejecutó `reporting-pipeline` |
| Endpoint con las filas de KPIs | ✅ | `GET /reporting/weekly-location-performance`, con la forma del briefing más `location_name` |
| KPIs según "KPIs a medir" | ✅ | Las 70 filas de una corrida coinciden con un cálculo independiente en SQL |
| Implementación coherente con `PIPELINE_DESIGN.md` | ✅ | Etapas, tablas, nombres y estrategias del diseño; los ajustes, con su motivo, en su sección 11 |

---

## Pipeline a producción: subflows, tests y dashboard

Parte 3 de 3 del pipeline del "Reporte Semanal de Costo y Merma por Local", en la rama `feature/pipeline-production`. Los entregables son `data/pipelines/pipeline.py` dividido en subflows, `tests/pipelines/test_pipeline.py` y el dashboard `/reporte-semanal` del backoffice. Coincide con el briefing y el enunciado en lo siguiente:

- **Subflows:** el flow principal coordina tres subflows con los nombres de etapa del diseño (`extract_weekly_location_performance_sources`, `transform_weekly_location_performance` y `load_weekly_location_performance`) y no contiene su lógica. Los dos pasos opcionales son subflows invocados con `return_state=True`. Cada subflow tiene entradas y salidas explícitas y se ejecuta solo en las pruebas.
- **Tasks por KPI:** el subflow de transformación tiene una task por KPI con el nombre de su columna del briefing; la lógica sigue en `data/process/`.
- **Tests:** `tests/pipelines/test_pipeline.py` prueba esas tasks aisladas, con eventos en memoria con la forma de `telemetry_events`: un test por KPI, los cinco KPIs calculados a mano y casos defensivos.
- **CLI:** `python data/pipelines/pipeline.py` sigue corriendo el ETL completo; el entrypoint y la documentación de la Parte 2 no cambiaron.
- **Dashboard:** cada KPI con su nombre exacto del briefing y lo que mide, el período de la semana, y datos reales de `reporting.weekly_location_performance` a través de `services/reporting/`.
- **Intactos:** `telemetry_events` (el pipeline solo lee, con un rol sin escritura), `services/telemetry/analysis.py` y `GET /telemetry/report`.

Las decisiones (J0 a J6) se tomaron con el desarrollador el 23 de noviembre de 2026. Están en la sección 12 de `data/pipelines/PIPELINE_DESIGN.md`, junto a la mejora adicional (señales de silencio) y la pregunta de diseño que responde.

> **Estado:** completa. Un commit por fase, hechos por el desarrollador: Fase 0 (estado del proyecto, `9689787`), Fase 1 (funciones por KPI, `e4f8275`), Fase 2 (subflows, `a527852`), Fase 3 (tests, `3f9bf0f`), Fase 4 (dashboard, `9b25bee`) y Fase 5 (documentación, con el mensaje del enunciado).

| Qué | Briefing o enunciado | Implementación | Motivo principal |
| --- | --- | --- | --- |
| Ruta del dashboard | "ej. `/reporting`" | `/reporte-semanal` | Las vistas del backoffice están en español; `/reporting` era un ejemplo |
| Entorno de los tests | `python -m pytest tests/pipelines/test_pipeline.py` | El mismo comando, con el entorno de `data/pipelines` activado (o `uv run --project data/pipelines`) | La raíz del monorepo no tiene entorno de Python propio |
| Nombres de los tests | Vocabulario del dominio y nombres de KPI del briefing | En español (`test_costo_de_compra_por_local_…`); el resto del monorepo los nombra en inglés | Los nombres de KPI del briefing están en español |
| Cómo se prueba una task | Tests unitarios aislados de las tasks | Cada test llama a la task con `.fn(...)` | Es la función que ejecuta Prefect, sin servidor ni base |
| Caché | Al menos una task de transformación con caché (Parte 2) | En `prepare_weekly_location_facts`, ya no en toda la transformación | Es la parte costosa; los KPIs son sumas y conteos sobre sus hechos |
| `failed_task` de la carga | `load_weekly_location_performance` (Parte 2) | `upsert_weekly_location_performance` | El nombre de etapa pasó al subflow; el log nombra la task concreta |
| Alertas de precio | "Le indica a Lucía cuándo necesita renegociar" | Conteo semanal por local; sin aviso al registrar la entrada ni detalle por producto | Fuera del alcance de la Parte 3; queda como tarea del inventario |
| Rutas nuevas en Docker | Sin especificar | `docker compose restart uis` tras añadir una ruta de `app/` | `next dev --webpack` del contenedor no detectó las carpetas nuevas |
| Mensaje del commit | `feat: refactor business performance pipeline into subflows, add unit tests, and add reporting dashboard` | En el último commit; los anteriores, un mensaje por fase | Un commit por fase, como el resto del proyecto |
| Destino del PR | "Sobre el PR de la Parte 2 o uno nuevo" | Uno nuevo, contra `feature/pipeline-implementation` | El PR #26 sigue abierto y conserva solo la Parte 2 |

### 1. El dashboard está en `/reporte-semanal`

El enunciado pone `/reporting` como ejemplo de ruta del backoffice. Todas las vistas del backoffice están en español (`/inventario`, `/proveedores`, `/gestor-incidencias`, `/telemetria`), y `AGENTS.md` pide seguir las convenciones locales. La ruta usa el nombre del entregable del briefing. La API sigue sirviendo `/reporting/...`, que es la que nombra el briefing.

**Coste:** la ruta de la vista y la de la API no coinciden.

### 2. Los tests usan el entorno de `data/pipelines`

`python -m pytest tests/pipelines/test_pipeline.py` pasa desde la raíz con el entorno de `data/pipelines` activado, que tiene Prefect, Pandas y los paquetes del pipeline. La raíz no tiene entorno de Python: cada proyecto del monorepo tiene el suyo, y `AGENTS.md` pide no añadir implementación a la raíz sin necesidad. Un `pyproject.toml` en la raíz habría sido un segundo entorno con Prefect que mantener. `tests/pipelines/README.md`, el diseño (§10) y el README de `data/pipelines` explican cómo activarlo.

**Coste:** con un `python` sin ese entorno, los tests fallan al importar.

### 3. Los tests llevan los nombres de KPI del briefing, en español

El enunciado pide que los nombres de los tests reflejen los nombres de KPI del briefing. Están en español, como los KPI de "KPIs a medir" (`test_costo_de_compra_por_local_suma_cantidad_por_costo_unitario_de_las_entradas`, `test_ratio_de_merma_es_cero_sin_compras_y_puede_superar_uno`). El resto del monorepo nombra sus pruebas en inglés.

### 4. Las tasks se prueban con `.fn(...)`

Cada test llama a la task del subflow de transformación con `.fn(...)`, la función que Prefect ejecuta, en lugar de lanzarla dentro de un flow. Así el test no necesita un servidor de Prefect ni una base, como pide el enunciado. El comportamiento de las tasks dentro de los subflows (reintentos, caché, estados) se prueba aparte, contra SQLite, en `data/pipelines/tests/`.

### 5. La caché pasa a la preparación de los hechos

En la Parte 2, la task con caché era la transformación entera. Al dividirla en una task por KPI, la caché queda en `prepare_weekly_location_facts` (refinar, validar y deduplicar), la parte costosa, con la misma clave (los `id` de los eventos, las semanas, el catálogo y la versión, que sube a 2). Los KPIs que siguen son sumas y conteos. El criterio de la Parte 2 (una task de transformación con `cache_key_fn` y `cache_expiration`) se sigue cumpliendo.

### 6. `failed_task` nombra la task del upsert

En la Parte 2, una carga fallida quedaba en el log con `failed_task = load_weekly_location_performance`. Ese nombre es ahora el del subflow de carga, y la task es `upsert_weekly_location_performance`. Cada subflow anota en la excepción la task que falló, así que el log sigue diciendo la task concreta aunque el error llegue a través del subflow.

**Coste:** las corridas fallidas anteriores y las nuevas usan nombres distintos para la misma etapa.

### 7. Las alertas de precio se quedan en el conteo semanal

El briefing define la frecuencia de alertas de precio como la señal para que Lucía renegocie. El reporte la da por local y semana, como pide la tabla de destino. Dos cosas quedan fuera de la Parte 3 (decisión del desarrollador, 2026-11-23) y se registran en el diseño (§8) como tarea del inventario:

- **Aviso al registrar:** quien registra una entrada con un coste anómalo no ve ningún aviso; el backoffice solo emite el evento.
- **Productos afectados:** Lucía no puede ver qué producto subió; hará falta un detalle por producto desde los eventos.

### 8. Una ruta nueva del backoffice exige reiniciar `uis` en Docker

`next dev --webpack`, como corre en el contenedor, no detectó las carpetas nuevas de `app/` (la página y las rutas del intermediario respondían 404) hasta `docker compose restart uis`. Los cambios en archivos existentes sí se detectan. Está documentado en el README del backoffice.

### 9. Commits por fase y PR nuevo

Como en el resto del proyecto, el trabajo va en un commit por fase y el último lleva el mensaje del enunciado. El enunciado permite construir sobre el PR de la Parte 2 o abrir uno nuevo: el PR nuevo apunta a `feature/pipeline-implementation`, y el #26 sigue con solo la Parte 2. Su descripción dice qué mejora adicional se implementó (las señales de silencio) y qué pregunta de diseño responde.

### Verificación de los criterios

| Criterio | Cumplimiento | Evidencia |
| --- | --- | --- |
| El flow principal invoca al menos tres subflows | ✅ | `weekly_location_performance_flow` llama a 3 subflows de etapa y 2 opcionales (diseño, §5.1) |
| Cada subflow con entradas y salidas explícitas, ejecutable solo | ✅ | Parámetros y retornos tipados (`WeeklyLocationPerformanceSources`, `WeeklyPerformanceResult`, filas escritas); pruebas de cada subflow por separado en `data/pipelines/tests/` |
| `tests/pipelines/test_pipeline.py` con al menos tres tests de tasks de transformación | ✅ | 10 tests: uno por KPI, los cinco a mano y cuatro defensivos |
| Tests aislados, con datos en memoria con forma de telemetría | ✅ | `.fn(...)` y eventos con `id`, `timestamp`, `event_type` y `tags`; sin base, APIs ni servidor de Prefect |
| Un test del comportamiento defensivo | ✅ | Eventos mal formados rechazados sin romper la corrida; tasks de KPI y ratio que fallan ante datos inválidos; semanas que no empiezan en lunes |
| Un test del valor de un KPI frente a su definición | ✅ | Los cinco KPIs de una semana de Medellín Centro, con las cuentas en el docstring (850 COP, 106,25, 0,125, 1 y 1) |
| `python -m pytest tests/pipelines/test_pipeline.py` pasa | ✅ | 10 pasan desde la raíz con el entorno de `data/pipelines` (apartado 2) |
| `python data/pipelines/pipeline.py` sigue corriendo el ETL completo | ✅ | Código 0, 5 subflows, 56 filas; contra Supabase, 70/70 filas iguales a un cálculo independiente en SQL |
| Nombres con el vocabulario del dominio y los KPI del briefing | ✅ | Subflows con el nombre del reporte; tasks y tests con los nombres de las columnas y de los KPI |
| `telemetry_events` y `analysis.py` sin modificar | ✅ | El pipeline lee `telemetry_events` con un rol sin escritura; `services/telemetry/` no cambió en la rama |
| Dashboard en `uis/backoffice/` con cada KPI etiquetado, desde `services/reporting/` | ✅ | `/reporte-semanal`: los cinco KPIs con su nombre del briefing, el período en palabras, vía `GET /reporting/weekly-location-performance` |
| Legible para un stakeholder no técnico | ✅ | Resumen por país, una sección por KPI con lo que mide, importes con su moneda, avisos en lenguaje llano; revisado por el desarrollador |

## Script nocturno de telemetría

Ticket #DEV-53, en la rama `feature/nightly-export`. `scripts/nightly_export.py` se ejecuta cada noche fuera de la API: exporta a CSV los `telemetry_events` del día anterior en UTC (o de `TARGET_DATE`), lanza el pipeline del Hito 6 como subproceso y registra cada ejecución en `ops.job_runs` (`pending → processing → completed | failed`), con `processing` como único lock e idempotencia por `(job_name, target_date)`. `job_runs` no sustituye a `reporting.pipeline_runs`: el script registra la orquestación y el pipeline sigue registrando su ETL. Coincide con el ticket en lo siguiente:

- **Modelo de datos:** `job_runs` con `id`, `job_name`, `target_date` (obligatorio), `status` con los cuatro valores exactos, `started_at`, `finished_at`, `error_message` y `created_at`; índice en `(job_name, target_date)`; migración `services/brasaland-api/migrations/006_job_runs.sql`; sin fusionar con `pipeline_runs`.
- **Script:** `scripts/nightly_export.py`, ejecutable con `python scripts/nightly_export.py` (con el entorno de `services/jobs`); `TARGET_DATE` o ayer en UTC; CSV solo si no existe; pipeline como subproceso tras el export; resultado en `job_runs`.
- **Control de estado:** módulo `job_runner` en `services/` (`services/jobs/job_runner.py`), con `has_processing_lock` y `has_completed_for_date`; toda excepción pasa la fila a `failed` con el mensaje y se registra en el log con su traza.
- **Disparador:** contenedor scheduler dedicado (`nightly-scheduler`, supercronic), fuera del proceso de FastAPI: sin APScheduler, `@repeat_every` ni hooks de `lifespan`.
- **Observabilidad:** `INFO` para inicio, fin, omisión y cancelación; `ERROR` para las excepciones; cada línea con timestamp, nombre del job y estado.

Las decisiones (N1 a N12) se tomaron con el desarrollador el 24 de noviembre de 2026; están al final de esta sección. El cambio en el pipeline del Hito 6 está en la §13 de `data/pipelines/PIPELINE_DESIGN.md`.

> **Estado:** completa. Un commit por fase, hechos por el desarrollador: Fase 0 (estado del proyecto, `44c142e`), Fase 1 (migración 006, `e975d44`), Fase 2 (`services/jobs`, `4a277bd`), Fase 3 (script, `0cbd48d`), Fase 4 (disparador, `6ec42eb`) y Fase 6 (documentación). La Fase 5, la verificación contra Supabase, no cambió el repositorio.

| Qué | Briefing o enunciado | Implementación | Motivo principal |
| --- | --- | --- | --- |
| Ruta del CSV | `data/raw/telemetry_YYYY-MM-DD.csv` | `data/raw/telemetry_exports/telemetry_YYYY-MM-DD.csv`, fuera de Git | Mantener ordenada `data/raw/` |
| Comando del pipeline | `python -m data.pipelines.telemetry_kpi_daily.run --no-prefect` "o tu entry point CLI del Hito 6" | `python data/pipelines/pipeline.py --week-from … --week-to … --trigger scheduled`, con Prefect | Es el entry point del Hito 6; no existe un pipeline diario ni un modo sin Prefect |
| Disparo programado del pipeline | Ejecución programada de los lunes (Partes 2 y 3) | Solo el job nocturno; la ejecución de Prefect se conserva sin horario | Un único programador para el mismo pipeline |
| "Registra la cancelación" y "registra omisión por duplicado" | Sin especificar dónde | En el log (`INFO`), sin fila nueva en `job_runs` | `status` solo admite los cuatro estados, y así dos ejecuciones dejan la tabla igual que una |
| "Sin tabla o columna lock aparte" | El estado `processing` es el lock | El estado `processing`, garantizado por un índice único parcial | Sin el índice, dos instancias simultáneas pueden pasar la comprobación a la vez |
| `TARGET_DATE` | Fechas arbitrarias | Fechas arbitrarias, siempre días ya terminados en UTC | El CSV de un día a medias quedaría incompleto para siempre |
| Destino del PR | `main` | `feature/pipeline-production` | Los PR #17 a #27 siguen abiertos |

### 1. Los CSV van en `data/raw/telemetry_exports/`

El ticket deja el archivo directamente en `data/raw/` (`telemetry_2025-01-15.csv`). Como se genera uno por noche, en pocas semanas `data/raw/` acumularía decenas de archivos junto a los datos fuente (`incidents-brasaland.csv`). Una subcarpeta propia mantiene `data/raw/` ordenada, como ya hace `data/raw/telemetry_events/` con las extracciones del pipeline. El nombre del archivo es el del ticket. La subcarpeta está fuera de Git: la columna `tags` lleva `user_id`, `session_id` y `request_id` seudonimizados, y un archivo diario haría crecer el repositorio sin límite.

**Coste:** la ruta no coincide con el ejemplo del ticket, y el respaldo solo existe en la máquina que ejecuta el script.

### 2. El pipeline se lanza con su CLI del Hito 6

El comando de referencia del ticket supone un pipeline diario con un modo sin Prefect. El del Hito 6 es semanal y siempre corre con Prefect. El script lo lanza como subproceso con `python data/pipelines/pipeline.py`, con su mismo intérprete, y le pasa las 4 semanas ISO cerradas a fecha de `target_date + 1`: sin `TARGET_DATE` equivale a la corrida por defecto, y con `TARGET_DATE` la ventana es siempre la misma para la misma fecha. Nunca escribe semanas incompletas en `reporting.weekly_location_performance`. El resultado se lee del código de salida (el pipeline cierra su `pipeline_runs` en `failed` y termina con error), con un tiempo máximo de 90 minutos. Sin `PREFECT_API_URL`, cada ejecución arranca un servidor temporal de Prefect.

El CLI suma la opción `--trigger {manual,scheduled}` (`manual` por defecto, el comportamiento anterior): el script pasa `scheduled`, y `pipeline_runs.trigger` sigue distinguiendo la corrida programada de las manuales, sin cambios en la migración 005 ni en la API.

**Coste:** casi todas las noches se recalculan semanas que no cambiaron (es idempotente y recoge los eventos que llegan tarde), y el servidor temporal añade unos segundos.

### 3. El job nocturno es el único disparador programado

Las Partes 2 y 3 dejaron una ejecución programada de Prefect los lunes a las 06:00 (America/Bogota) sobre las mismas 4 semanas que ahora recalcula el job nocturno. Mantener las dos habría duplicado el cálculo de los lunes y repartido las ejecuciones programadas entre `job_runs` y Prefect. Además, si coincidieran, la segunda fallaría (una sola corrida activa por pipeline). Se quita solo el horario: la ejecución de Prefect sigue existiendo para `POST /reporting/pipeline-runs` y el disparo manual del backoffice. El lunes por la mañana los datos están igual de frescos, porque la corrida de esa noche (08:00 UTC, 03:00 en Bogotá) ya incluye la semana cerrada el domingo.

**Coste:** cambia un detalle de las Partes 2 y 3; `PIPELINE_DESIGN.md` (§5.4, §10 y §13) y los README del pipeline lo explican.

### 4. La cancelación y la omisión se registran en el log

El ticket pide que la instancia bloqueada "registre la cancelación" y que la ejecución repetida "registre la omisión por duplicado", pero `status` solo admite `pending`, `processing`, `completed` y `failed`, con los valores exactos del ticket. Escribirlas como `failed` daría falsos fallos, y como `completed`, ejecuciones que no hicieron nada; con una columna nueva, la tabla tampoco quedaría igual tras dos ejecuciones. Por eso se registran en el log con nivel `INFO` (timestamp, job, estado `skipped` o `cancelled` y fecha), que es donde el apartado de observabilidad pide la omisión por duplicado, y las comprobaciones se hacen antes de crear la fila `pending`. Así, ejecutar dos veces deja `job_runs` exactamente igual que una vez.

La única excepción es la instancia que pierde la carrera del índice (apartado 5): ya había creado su fila `pending`, que no puede quedarse así, y la cierra como `failed` con `error_message = 'lock_held: …'`.

**Coste:** la cancelación y la omisión normales no dejan rastro en la base, solo en el log.

### 5. Un índice único parcial garantiza el lock

El lock es el estado `processing`, como pide el ticket. Pero si cada instancia comprueba `has_processing_lock` y después pasa su fila a `processing`, dos instancias lanzadas a la vez pueden pasar la comprobación en el mismo instante, justo la prueba del criterio de evaluación. El índice único parcial `uq_job_runs_one_processing ON ops.job_runs (job_name) WHERE status = 'processing'` hace que la segunda transición falle de forma atómica. No guarda nada nuevo: no es una tabla ni una columna de lock, solo impide que el estado `processing` se duplique. Es el mismo patrón que `uq_pipeline_runs_one_active` del pipeline. En la verificación contra Supabase, dos instancias pasaron la comprobación en el mismo segundo y el índice decidió.

**Coste:** un revisor estricto podría verlo como un mecanismo aparte; este apartado lo justifica.

### 6. `TARGET_DATE` solo admite días terminados

`TARGET_DATE` acepta cualquier fecha anterior a hoy en UTC. Con hoy o una fecha futura, el script termina con código 2 sin crear ninguna fila: el CSV de un día sin terminar quedaría incompleto y, como nunca se sobrescribe, ese día no se volvería a exportar. El formato también se valida estrictamente (`YYYY-MM-DD`).

**Coste:** ninguno práctico; para volver a exportar un día hay que borrar su CSV.

### 7. El PR va contra la rama anterior

El ticket pide el PR hacia `main`. Como los PR #17 a #27 siguen abiertos, el PR va contra `feature/pipeline-production`, como el resto de la cadena, para que solo muestre los commits de este ticket.

### Decisiones

- **N1, semanas:** las 4 semanas ISO cerradas a fecha de `target_date + 1`.
- **N2, pipeline:** subproceso con el CLI del Hito 6, con Prefect; resultado por el código de salida.
- **N3, un disparador:** se quita el horario de los lunes del deployment de Prefect.
- **N4, CSV:** `data/raw/telemetry_exports/`, fuera de Git (apartado 1).
- **N5, `job_runner`:** paquete `services/jobs/` (`brasaland-jobs`), solo SQLAlchemy y psycopg2, sin FastAPI.
- **N6, esquema:** `ops.job_runs`, un esquema propio para la capa de orquestación, como `reporting` para la de negocio.
- **N7, rol:** `nightly_jobs`, que solo lee `telemetry_events` y lee, inserta y actualiza `ops.job_runs` (sin `DELETE`); `JOBS_DATABASE_URL`.
- **N8, disparador:** contenedor `nightly-scheduler` con supercronic v0.2.51 (sha256 fijado), `0 8 * * *` en UTC: 03:00 en Bogotá y 03:00 o 04:00 en Florida, sin actividad en los locales y con 8 horas de margen para la telemetría que llega tarde. Se eligió frente al crontab del sistema operativo porque el equipo de desarrollo es Windows (sin crontab) y porque el contenedor es reproducible y es la opción que el ticket recomienda para producción.
- **N9, atomicidad del lock:** índice único parcial (apartado 5).
- **N10, cancelación y omisión:** en el log (apartado 4).
- **N11, filas abandonadas:** `SIGTERM` pasa por el `finally`; un `SIGKILL` no, así que al arrancar se cierran como `failed` (`abandoned: …`) las filas abiertas con más de `NIGHTLY_STALE_MINUTES` (120). El tiempo máximo del pipeline (90) debe ser menor.
- **N12, `--trigger`:** la corrida del script queda como `scheduled` en `pipeline_runs` (apartado 2).

### Verificación de los criterios

Contra Supabase el 24 de noviembre de 2026, con la telemetría real (entorno `development`), desde el host y desde el contenedor `nightly-scheduler`.

| Criterio | Cumplimiento | Evidencia |
| --- | --- | --- |
| Proceso independiente: no importa ni ejecuta código de FastAPI en el hilo principal | ✅ | `services/jobs` no depende de FastAPI; una prueba importa el script en un proceso nuevo y comprueba que no carga `fastapi`, `starlette`, `app` ni `prefect`; el disparo es un contenedor aparte |
| Máquina de estados implementada y `job_runs` refleja el estado real, con `target_date` | ✅ | 9 ejecuciones reales: 6 `completed` y 3 `failed` (`lock_held`, `PipelineFailed` y `abandoned`), cada una con su fecha, sus timestamps y su mensaje |
| `processing` como lock sin mecanismo aparte, demostrable con dos instancias a la vez | ✅ | Dos instancias lanzadas a la vez: una `completed`, la otra cancelada por el índice (`lock_held`); una segunda instancia 3 s después, cancelada sin fila |
| Idempotente por `target_date`: dos ejecuciones el mismo día equivalen a una | ✅ | La segunda ejecución del 23-nov se omitió: sin fila nueva, CSV idéntico (sha256) y sin relanzar el pipeline; desde el contenedor, la misma fecha cada 20 s: una `completed` y el resto omitidas |
| Ningún registro queda en `processing` tras un fallo (`try/except/finally`) | ✅ | Fallo forzado del pipeline: `failed` con `PipelineFailed: …` y código 1; `docker kill` (SIGKILL) a mitad: la fila quedó en `processing` y la siguiente ejecución la cerró como `abandoned`; estado final sin filas en `processing` |
| CSV en `data/raw/` con el nombre correcto y los datos de `telemetry_events` del día (solo backup) | ✅ | `data/raw/telemetry_exports/telemetry_2026-11-23.csv` con las 106 filas del día; el pipeline sigue leyendo de la base (apartado 1) |
| `job_runs` y `pipeline_runs` coexisten sin duplicar responsabilidades | ✅ | 6 corridas `scheduled` en `pipeline_runs`, una por cada `completed` de `job_runs`; las ejecuciones canceladas, omitidas o muertas antes del pipeline no dejan corrida |
| Logs con timestamp, nombre del job y estado en cada evento | ✅ | `2026-11-24T12:12:15Z \| INFO \| nightly_export \| processing \| target_date=2026-11-23 \| …`; `ERROR` con la traza en los fallos |
| Disparador configurado y expresión cron documentada en el PR | ✅ | `scripts/nightly_export.crontab` (`0 8 * * *`, UTC) en el servicio `nightly-scheduler`; `supercronic -test` lo da por válido y lanzó el script desde el contenedor |
| `TARGET_DATE` permite ejecutar el script sobre fechas arbitrarias | ✅ | Ejecuciones del 18 al 23 de noviembre con `TARGET_DATE`, sin tocar el código (apartado 6) |

## Cola de tareas asíncronas

Ticket #DEV-55, en la rama `feature/async-tasks`. El informe técnico de telemetría deja de calcularse dentro de la petición. La API lo encola en Redis y responde `202 Accepted` con un `task_id`; un worker de Celery, en un proceso aparte, lo calcula, y `GET /tasks/{task_id}` devuelve su estado (`pending`, `started`, `success`, `failure`) y el resultado. Los fallos acaban en una Dead Letter Queue registrada en base de datos, y Flower permite seguir la cola.

**Operación elegida:** `GET /telemetry/report`. El ticket pide convertir "la que más tarde en responder", y se midieron los dos candidatos con el mismo procedimiento que `docs/CACHING_REPORT.md` (API local, 1 calentamiento + 30 peticiones, tiempos de `api.timing`):

- **Informe:** 266 ms de mediana en 7 días y 253 ms en 90 días, sin caché. Su coste crece con la telemetría acumulada.
- **`POST /incidents/analyze`:** 224 ms con un CSV de 4,9 MB. Es prácticamente su máximo, porque la API rechaza archivos de más de 5 MB.
- **`GET /inventory/orders`:** no se convierte. Es un listado frecuente con caché, y su respuesta (5,8 MB) no cabe bien en un backend de resultados.

Las decisiones (T1 a T14) se tomaron con el desarrollador el 24 de noviembre de 2026.

> **Estado:** en curso. Esta sección se completa con la tabla de criterios al cerrar la tarea.

| Qué | Briefing o enunciado | Implementación | Motivo principal |
| --- | --- | --- | --- |
| Método del endpoint convertido | "El endpoint que antes ejecutaba la operación pesada ahora encola la tarea" | `POST /telemetry/report` (mismo path), y el `GET` desaparece | Un `GET` que crea trabajo no es seguro en HTTP |
| Módulo Celery | `services/celery_app.py` "o similar"; `uv add celery redis flower` | `services/tasks/brasaland_tasks/celery_app.py`, en el proyecto uv `brasaland-tasks` | Cada paquete de `services/` es un proyecto uv propio; no hay un proyecto en la raíz |
| "Si una tarea falla hasta tres veces" | `max_retries=3` | `max_retries=3`: tres reintentos, es decir, cuatro ejecuciones; la DLQ registra `attempt=4` | El checklist fija el valor de `max_retries` |
| Qué llega a la DLQ | Las tareas que superan `max_retries` | Esas, y también los fallos permanentes, que no se reintentan (con `attempt=1`) | Que ningún fallo final quede solo en el log |
| Destino del PR | Sin especificar (`main` en los anteriores) | `feature/nightly-export` | Los PR #17 a #28 siguen abiertos |

### 1. El informe se pide con `POST`

El ticket pide que el endpoint que antes ejecutaba la operación la encole y devuelva `202` con el `task_id`. Si se quedara como `GET`, crear una tarea sería un efecto lateral de una petición que HTTP considera segura. Los reintentos automáticos, la precarga del navegador o recargar la página encolarían informes repetidos. Por eso el endpoint pasa a `POST /telemetry/report`, con el mismo path; las fechas van en el cuerpo, con la misma validación que antes.

Para que repetir la petición no cree trabajo, los mismos parámetros devuelven el mismo `task_id` mientras la tarea vive y 60 s después de que termine con éxito. Ese registro en Redis sustituye a la caché en memoria de 60 s del informe (`X-Cache`), y ahora es compartido entre procesos.

**Coste:** cambia el contrato del informe (método y forma de la respuesta). El backoffice se adapta en la misma tarea.

### 2. Los "tres fallos" son tres reintentos

En Celery, `max_retries=3` permite tres reintentos además de la ejecución original: cuatro ejecuciones en total. El checklist fija ese valor y dice que la tarea pasa a la DLQ "cuando supera `max_retries`". Por eso se mantiene `max_retries=3`, y la DLQ guarda el número real de la última ejecución (4). Las esperas entre intentos son de 10, 20 y 40 s.

**Coste:** el enunciado habla de "tres fallos" y el registro muestra el intento 4. El PR lo explica.

