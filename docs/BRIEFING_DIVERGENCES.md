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
| Ninguna ruta abierta por olvido | `tests/test_protected_routes.py` sobre `/openapi.json` | Solo son públicas `POST /auth/login`, `POST /users` y `GET /health`. Al quitar la protección de `suppliers`, la prueba falla |
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
