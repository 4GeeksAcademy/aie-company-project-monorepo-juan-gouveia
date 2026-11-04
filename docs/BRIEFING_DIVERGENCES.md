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

---

## Procesador de reportes de incidentes

Los valores del análisis coinciden exactamente con el briefing; las diferencias son de ubicación, rutas y textos, y cada una tiene un motivo. Cubre las dos fases del ejercicio: el script de análisis (Fase 1) y su integración en la plataforma con API y backoffice (Fase 2).

| Qué | Consigna o briefing | Implementación | Motivo principal |
| --- | --- | --- | --- |
| Carpeta del script | `incidents-analysis/` (briefing) | `scripts/incident-report/` | La consigna pide `/scripts` |
| Carpeta del backend | `/services/api` | `services/brasaland-api/` | Propuesta de arquitectura del CTO |
| Rutas de la API | `/api/incidents/...` | `/api/v1/incidents/...` | Versión única de la API (propuesta) |
| Lógica compartida | Extraída a módulos compartidos | `service.py` en la API, importado por el script | El backend es la fuente de verdad |
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

### 3. Lógica compartida en `service.py`

La validación y el análisis existen una sola vez, en `services/brasaland-api/app/domains/incidents/service.py`; el script y la API la importan.

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
| El JWT lleva solo `sub` (el `id`), `iat` y `exp`, firmado con HS256 | "El token debe llevar como mínimo el ID del usuario"; el rol se lee de TinyDB en cada petición, así un cambio de rol o una desactivación aplica al momento | No hay revocación de tokens: un token robado vale hasta que caduca, salvo que se desactive o borre la cuenta |
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
| `/incidencias` y `/proveedores` del backoffice reciben 401 | El briefing lo da por esperado: el frontend enviará el token en una fase posterior | Esas herramientas no funcionan hasta entonces |

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
| Ninguna ruta abierta por olvido | `tests/test_protected_routes.py` sobre `/openapi.json` | Solo son públicas `POST /auth/login`, `POST /users` y `GET /health`. Al quitar la protección de `suppliers`, la prueba falla |
| Primer admin | `uv run create-admin` con datos inválidos | Mensaje en español y no escribe nada; los casos válidos están cubiertos por pruebas |
