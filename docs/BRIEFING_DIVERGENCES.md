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
| Menú en móvil y tablet | Registro "accesible desde el menú de la aplicación" | Desde `xl`, en la cabecera; por debajo, en la portada (logo), que es el menú en esas pantallas | Con 6 herramientas, la cabecera no tiene sitio en pantallas pequeñas (decisión del desarrollador) |
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

La consigna pide que la página de registro sea "accesible desde el menú de la aplicación". Desde 1280 px (`xl`), la cabecera muestra los enlaces a las 6 herramientas, entre ellos "Registrar incidencia" y "Gestor de incidencias". Por debajo, el desarrollador pidió que la tablet se comporte como el móvil: la cabecera solo muestra el logo y la cuenta, y se navega desde la portada, que tiene una tarjeta por herramienta (las dos del gestor incluidas). Con 6 herramientas, los enlaces no caben junto a la cuenta y no pueden pasar a una segunda línea, porque la barra de filtros de `/talento` depende de la altura fija de la cabecera.

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
| Códigos HTTP correctos en éxito y error | `tests/domains/incidents/test_manager_router.py`; rutas protegidas | 201, 200, 400, 404 y 401 sin token |
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
