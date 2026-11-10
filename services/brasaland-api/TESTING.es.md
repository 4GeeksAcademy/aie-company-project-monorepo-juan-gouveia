# Pruebas de la API de Brasaland

> **Estado (2026-11-10): batería completa (ticket AUTH-088).** El plan de casos se escribió y revisó antes de escribir ninguna prueba; después se implementó entero. Pasan las 806 pruebas de pytest y las 55 de Jest. Con solo `tests/auth/`, la cobertura de los módulos de autenticación es del **88 %** (objetivo: 70 %). La batería encontró dos bugs, ya corregidos (ver "Bugs encontrados"). El extra API-042 (proveedores y gestor de incidencias) está completo: **84 %** con solo sus módulos (objetivo: 60 %).

> _Versión en inglés: [TESTING.md](./TESTING.md)._

## Suites

| Suite | Carpeta | Qué comprueba |
|---|---|---|
| **Unitarias de autenticación** (AUTH-088) | `tests/auth/` | La lógica de cada endpoint de autenticación: qué decide, no cómo responde. Llaman directamente a las funciones de cada ruta y a sus servicios, sin cliente HTTP. **16 módulos y 146 casos**: `test_token.py` y uno por cada uno de los 15 endpoints. |
| **Unitarias de proveedores e incidencias** (API-042) | `tests/suppliers/` y `tests/incidents/` | La lógica de los 6 endpoints del directorio de proveedores y los 5 del gestor de incidencias, sin HTTP. **11 módulos y 101 casos**. Ver "API-042: proveedores y gestor de incidencias". |
| **Integración HTTP** | `tests/integration/` | El contrato HTTP con el backoffice: rutas protegidas, códigos de estado, formato `{"error": {...}}` y cabeceras. Son las pruebas de router que ya existían: 99 de autenticación (214 casos con la parametrización), más las de proveedores, el gestor y el analizador de incidencias (60 pruebas y 90 casos, movidas en API-042). En total, 304 casos. Llevan el marker `integration`, que `tests/integration/conftest.py` aplica a toda la carpeta. |
| **Resto de la API** | `tests/core/` y `tests/domains/` | Configuración, seguridad, correo, errores, `create-admin`, y los modelos, repositorios y seeds de cada dominio. |
| **Jest del backoffice** (AUTH-088) | `uis/backoffice/__tests__/auth/` | La lógica TypeScript de autenticación del backoffice: validación de formularios, destino tras el login, token en `localStorage` y reparto de los errores de la API. 55 pruebas. Ver "Pruebas del backoffice (Jest)". |

## Cómo ejecutarlas

### API (pytest)

Desde `services/brasaland-api/`:

```bash
uv sync --extra dev                      # instala pytest, pytest-cov y httpx
uv run pytest                            # toda la batería (806 pruebas, unos 2,5 min por bcrypt)
uv run pytest tests/auth                 # solo las unitarias de autenticación (146, unos 45 s)
uv run pytest tests/suppliers tests/incidents   # solo las de API-042 (101, unos 2 s)
uv run pytest -m integration             # solo las pruebas de integración HTTP
uv run pytest -m "not integration"       # todo menos las pruebas HTTP
uv run pytest --cov                      # toda la batería con la cobertura de app/
```

Cobertura de los módulos de autenticación con solo la batería unitaria (la cifra del objetivo del 70 %):

```bash
uv run pytest tests/auth --cov=app.core.security --cov=app.domains.auth \
  --cov=app.domains.users --cov=app.domains.profiles
```

Cobertura de API-042 con solo sus módulos (objetivo del 60 %):

```bash
uv run pytest tests/suppliers tests/incidents --cov=app.domains.suppliers --cov=app.domains.incidents
```

No hace falta `.env`: `tests/conftest.py` fija una `SECRET_KEY` de pruebas, usa bases TinyDB temporales y un emisor de correo falso. Ninguna prueba toca `storage/` ni envía correos.

### Backoffice (Jest)

Desde `uis/backoffice/`, de forma independiente de la API:

```bash
npm install
npm test                                 # las 55 pruebas de __tests__/
npm run test:coverage                    # lo mismo con cobertura (equivale a jest --coverage; informe en coverage/)
```

## Criterios del plan

- **Lógica, no HTTP.** Cada prueba afirma una decisión de la aplicación: qué token se emite, qué `ApiError` se lanza y con qué código, qué queda guardado en la base. No se comprueba el JSON, los códigos que pone FastAPI ni la validación del cuerpo por el framework. Las reglas de nuestros modelos (longitud de contraseña, campos prohibidos) sí se prueban, porque son reglas de negocio.
- **Sin HTTP ni red.** Las pruebas usan una base TinyDB temporal y el emisor de correo falso (`tests/conftest.py`). El tiempo se controla con los parámetros `now` y `expires_delta` de la lógica y con un reloj controlado, nunca con esperas (ver "Cómo están construidas").
- **Prioridades**, en este orden:
  1. **la caducidad de los tokens**, porque es la regresión que motivó el ticket;
  2. **las decisiones de seguridad**: no revelar qué emails existen, no escalar privilegios y cerrar las sesiones al cambiar la contraseña;
  3. **los límites de las reglas de entrada**.
- **Tres niveles por endpoint:** camino feliz (**F**), caso límite (**L**) y modo de fallo (**X**). Los casos marcados con **(IA)** salieron de la revisión asistida por IA (ver más abajo).
- **Un módulo por endpoint**, más `test_token.py` para la generación y validación de tokens, que usan todos los endpoints protegidos.

## Casos por módulo

### `test_token.py` — tokens de acceso y validación de la sesión

Cubre `core/security.py` (crear y decodificar) y `get_current_user`, la dependencia de todas las rutas protegidas.

| ID | Caso | Decisión esperada | Por qué |
|---|---|---|---|
| TOK-F1 | Crear un token | Lleva `sub` = ID del usuario; `exp − iat` = `ACCESS_TOKEN_EXPIRE_MINUTES` × 60 | Detecta un cambio de unidades (segundos frente a minutos), justo el tipo de refactor del incidente |
| TOK-F2 | Token válido en `get_current_user` | Devuelve el usuario de la base | El camino de todas las rutas protegidas |
| TOK-L1 | Token emitido hace (duración − 1 s) y hace (duración + 1 s) | El primero vale; el segundo, `TokenExpiredError` | La frontera exacta de la caducidad |
| TOK-L2 | Cambiar `ACCESS_TOKEN_EXPIRE_MINUTES` | La duración del token sigue al ajuste | Que la duración no quede fija en el código |
| TOK-L3 **(IA)** | Token emitido en el mismo segundo que un cambio de contraseña, y un segundo antes | El primero vale; el segundo, 401 `session_revoked` | `iat` va en segundos: es un límite conocido y aceptado de AUTH-03 |
| TOK-X1 | Token caducado en `get_current_user` | 401 `token_expired`, distinto de `invalid_token` | El backoffice muestra "la sesión caducó" solo con este código |
| TOK-X2 | Token mal formado, vacío, con otra firma, sin `sub` o con `sub` vacío | 401 `invalid_token` | Entradas manipuladas |
| TOK-X3 **(IA)** | Token con `"alg": "none"` | 401 `invalid_token` | Ataque clásico de JWT: aceptar un token sin firma |
| TOK-X4 | Token de restablecimiento usado como sesión | 401 `invalid_token` | Un enlace del correo no puede abrir sesión |
| TOK-X5 | Sin token | 401 `not_authenticated` | |
| TOK-X6 | Token de un usuario borrado, de una cuenta desactivada y emitido antes de un cambio de contraseña | 401 `invalid_token`, 403 `inactive_user` y 401 `session_revoked` | Una firma válida no basta: manda el estado actual de la cuenta |

### `test_login.py` — `POST /auth/login`

| ID | Caso | Decisión esperada | Por qué |
|---|---|---|---|
| LOG-F1 | Email y contraseña correctos | Token válido cuyo `sub` es el usuario | |
| LOG-L1 | Email con mayúsculas y espacios alrededor | Encuentra al mismo usuario | El email se guarda normalizado |
| LOG-L2 | Email o contraseña vacíos | Los rechaza la regla de `LoginRequest` | "Campo vacío" del ticket |
| LOG-L3 **(IA)** | Contraseña de más de 72 bytes | 401 `invalid_credentials`, sin error interno | bcrypt rechaza esas contraseñas; `verify_password` debe devolver `False` |
| LOG-X1 | Contraseña incorrecta y email inexistente | El mismo 401 `invalid_credentials` en ambos casos | No revelar qué emails están registrados |
| LOG-X2 | Cuenta desactivada con la contraseña correcta | 403 `inactive_user` y ningún token | |
| LOG-X3 **(IA)** | Cuenta desactivada con una contraseña incorrecta | 401 `invalid_credentials`, no 403 | Sin la contraseña no se revela que la cuenta existe y está desactivada |

### `test_me.py` — `GET /auth/me`

| ID | Caso | Decisión esperada |
|---|---|---|
| ME-F1 | Usuario con perfil | ID, email, rol y perfil del usuario del token |
| ME-L1 | Usuario sin perfil | `profile` vacío, sin error |
| ME-X1 | Token de un usuario borrado | No llega a la ruta: 401 `invalid_token` |

### `test_forgot_password.py` — `POST /auth/forgot-password`

| ID | Caso | Decisión esperada | Por qué |
|---|---|---|---|
| FGT-F1 | Email de una cuenta activa | Crea el enlace (caduca en `PASSWORD_RESET_EXPIRE_MINUTES`) y programa un correo al usuario con su nombre y un enlace con token | |
| FGT-L1 | Cuarta solicitud en una hora, y otra pasada la hora | La cuarta no crea enlace ni correo; pasada la hora, sí | Límite de 3 por hora (P-9 de AUTH-03) |
| FGT-L2 | Email en mayúsculas; usuario sin perfil | Encuentra la cuenta; el correo sale sin nombre | |
| FGT-X1 | Email inexistente y cuenta desactivada | Ningún enlace ni correo, y **el mismo mensaje** que en FGT-F1 | No revelar qué cuentas existen |

### `test_validate_reset_token.py` — `POST /auth/reset-password/validate`

| ID | Caso | Decisión esperada | Por qué |
|---|---|---|---|
| VAL-F1 | Enlace válido | Lo acepta y **no lo consume**: después sirve para restablecer | Solo comprueba |
| VAL-L1 | Un segundo antes de la caducidad y en el instante exacto | El primero es válido; el segundo, `reset_token_expired` | Frontera: la base lo da por caducado en el mismo instante (`expires_at <= now`) |
| VAL-X1 | Enlace usado; texto que no es un token; token de acceso en su lugar | `reset_token_used`; `invalid_reset_token`; `invalid_reset_token` | |
| VAL-X2 **(IA)** | Token con el `jti` de un enlace de otro usuario | `invalid_reset_token` | El enlace debe pertenecer al usuario del token |
| VAL-X3 | Usuario desactivado o borrado después de pedir el enlace | `invalid_reset_token` | |

### `test_reset_password.py` — `POST /auth/reset-password`

| ID | Caso | Decisión esperada | Por qué |
|---|---|---|---|
| RST-F1 | Enlace válido y contraseña nueva | La nueva sirve y la anterior no; el enlace queda usado; se guarda `password_changed_at` y las sesiones anteriores dan `session_revoked` | |
| RST-L1 | Dos enlaces pendientes; se usa uno | El otro también queda anulado | |
| RST-L2 | Contraseña nueva de 8 caracteres y de 72 bytes; de 7 caracteres y de 73 bytes (con acentos) | Las dos primeras valen; las dos últimas, no | Las reglas son las del registro; los acentos ocupan 2 bytes |
| RST-X1 | Enlace usado, caducado o no válido | Su código (`reset_token_used`, `reset_token_expired`, `invalid_reset_token`) y **la contraseña no cambia** | Un fallo no deja la cuenta a medias |

### `test_change_password.py` — `POST /auth/change-password`

| ID | Caso | Decisión esperada | Por qué |
|---|---|---|---|
| CHG-F1 | Contraseña actual correcta | Guarda la nueva; el token devuelto vale y el anterior da `session_revoked`; los enlaces pendientes quedan anulados | |
| CHG-L1 | Contraseña nueva igual a la actual | Se acepta y se revocan las sesiones | Documenta la decisión actual: no hay regla en contra |
| CHG-L2 | Contraseña actual vacía; nueva de 7 caracteres | Las rechazan las reglas de `ChangePasswordRequest` | |
| CHG-X1 | Contraseña actual incorrecta | 400 `invalid_current_password`; la contraseña, las sesiones y los enlaces no cambian | |
| CHG-X2 | La cuenta se borra entre la autenticación y el cambio | 401 `invalid_token`, lo mismo que responde `get_current_user` a un usuario borrado | Prueba de regresión del bug H-2 (ver "Bugs encontrados") |

### `test_register.py` — `POST /users`

| ID | Caso | Decisión esperada | Por qué |
|---|---|---|---|
| REG-F1 | Datos válidos con perfil | Usuario `user`, activo, email en minúsculas, contraseña solo como hash bcrypt verificable; perfil con los datos enviados | |
| REG-L1 | Sin datos de perfil | Perfil creado con los campos vacíos | Siempre hay un perfil por usuario |
| REG-L2 | Contraseña de 8 caracteres y de 72 bytes; de 7 y de 73 bytes | Las primeras valen; las otras, no | |
| REG-L3 | Email ya registrado con otra capitalización o con espacios | 409 `duplicate_email` y no se crea nada | "Usuario duplicado" del ticket |
| REG-X1 | Se envía `role: admin` | Lo rechaza el modelo (campo no permitido) | Nadie se registra como admin |
| REG-X2 | Email con formato no válido | Lo rechaza el modelo | |
| REG-X3 | Falla la creación del perfil | El usuario no queda guardado | Sin perfil no hay usuario |

### `test_list_users.py` — `GET /users`

| ID | Caso | Decisión esperada |
|---|---|---|
| LST-F1 | Un admin lista | Todas las cuentas, sin hash de contraseña |
| LST-L1 | Solo existe el admin | Una sola cuenta |
| LST-X1 | Lo pide un `user` o un `manager` | 403 `forbidden` |

### `test_get_user.py` — `GET /users/{id}`

| ID | Caso | Decisión esperada | Por qué |
|---|---|---|---|
| GET-F1 | Un usuario pide su cuenta; un admin pide otra | Los datos, sin hash | |
| GET-L1 | Un admin pide un ID inexistente | 404 `user_not_found` | |
| GET-X1 | Un usuario pide otra cuenta, exista o no | 403 en ambos casos | El 403 va antes de buscar: no revela si el ID existe |

### `test_update_user.py` — `PUT /users/{id}`

| ID | Caso | Decisión esperada | Por qué |
|---|---|---|---|
| UPD-F1 | Un usuario cambia su email y su contraseña; un admin cambia el rol y el estado de otro | Se guardan; la contraseña, como hash | |
| UPD-L1 | Cambiar al propio email; cambiar al de otra cuenta con otra capitalización | El primero se acepta; el segundo da 409 `duplicate_email` | |
| UPD-L2 | Cuerpo vacío o campos a `null` | Los rechaza `UserUpdate` | |
| UPD-X1 | Un `user` o un `manager` intenta cambiar `role` o `is_active`, aunque sea en su cuenta | 403 y nada cambia | Escalada de privilegios |
| UPD-X2 | Un usuario edita otra cuenta; un admin edita un ID inexistente | 403 y 404 | |
| UPD-X3 **(IA)** | Un usuario cambia su contraseña por esta ruta | Se cierran las sesiones anteriores y se anulan los enlaces pendientes, como en AUTH-03; también cuando un admin cambia la contraseña de otra cuenta. Cambiar solo el email no cierra nada | Prueba de regresión del bug H-1 (ver "Bugs encontrados") |

### `test_delete_user.py` — `DELETE /users/{id}`

| ID | Caso | Decisión esperada |
|---|---|---|
| DEL-F1 | Un usuario borra su cuenta | Se borran el usuario, su perfil y sus enlaces de restablecimiento; su token deja de valer |
| DEL-L1 | Un admin borra otra cuenta | Se borra |
| DEL-X1 | Un usuario intenta borrar otra cuenta; un admin borra un ID inexistente | 403 sin borrar nada; 404 |

### `test_get_my_profile.py` — `GET /profiles/me`

| ID | Caso | Decisión esperada |
|---|---|---|
| PME-F1 | Usuario con perfil | Su perfil |
| PME-L1 | Perfil con todos los campos vacíos | El perfil, con los campos vacíos |
| PME-X1 | Usuario cuyo perfil no existe | 404 `profile_not_found` |

### `test_update_my_profile.py` — `PUT /profiles/me`

| ID | Caso | Decisión esperada | Por qué |
|---|---|---|---|
| UPM-F1 | Se envía solo el teléfono | Cambia el teléfono; el resto sigue igual | Actualización parcial |
| UPM-L1 | `null` en un campo; texto con espacios alrededor; longitudes máximas (120, 30 y 200) y una más | Vacía el campo; recorta; acepta el máximo y rechaza el siguiente | |
| UPM-X1 | Cuerpo vacío, campo desconocido o nombre solo con espacios | Lo rechaza `ProfileUpdate` | |
| UPM-X2 | Usuario sin perfil | 404 `profile_not_found` | |

### `test_get_profile.py` — `GET /profiles/{user_id}`

| ID | Caso | Decisión esperada | Por qué |
|---|---|---|---|
| GPR-F1 | El dueño lo pide; un admin pide otro | El perfil | |
| GPR-L1 **(IA)** | Un `manager` pide otro perfil | 403 | `manager` no es admin |
| GPR-X1 | Un usuario pide otro perfil; un admin pide uno inexistente | 403 y 404 | |

### `test_update_profile.py` — `PUT /profiles/{user_id}`

| ID | Caso | Decisión esperada | Por qué |
|---|---|---|---|
| UPR-F1 | El dueño actualiza su perfil por su ID | Se guarda | |
| UPR-L1 | Un admin intenta actualizar otro perfil | 403 | Regla de AUTH-01: solo el dueño modifica su perfil, también frente a un admin |
| UPR-X1 | Un usuario intenta actualizar otro perfil; el dueño no tiene perfil | 403 sin cambios; 404 | |

## Cómo están construidas

- **Llamada directa a la lógica.** Cada prueba llama a la función de la ruta (por ejemplo, `register_user(data, store=...)`) o a su servicio, con los argumentos que inyectaría FastAPI. Afirma el `ApiError` lanzado (estado y código, con `raises_api_error`) o lo guardado en la base, nunca el JSON de la respuesta.
- **Decisión del login separada.** La ruta `POST /auth/login` recibe la petición cruda para aceptar JSON y formulario, así que su decisión (401, 403 o token) se movió a `issue_login_token` para probarla sin HTTP. Es el único cambio de código de producción hecho para las pruebas; no cambia el comportamiento.
- **Reloj controlado (`clock`).** Empieza en el instante real, en segundos enteros como `iat`, y solo avanza con `clock.advance(...)`. python-jose comprueba la caducidad con su propio `datetime.now`, así que el fixture se lo sustituye por `clock.now`: la frontera de caducidad se prueba al segundo exacto (TOK-L1), sin esperas ni pruebas inestables. Si una versión de jose cambia cómo lee la hora, un `assert` del fixture lo avisa.
- **Rutas async** (`forgot-password`, `reset-password`, `change-password`…) con `@pytest.mark.anyio`, del plugin de anyio que ya instala FastAPI.
- **Fixtures** (`tests/auth/conftest.py`): `user_factory`, `active_user`, `inactive_user`, `admin_user` y `clock`. Utilidades en `tests/auth/helpers.py`: `raises_api_error`, `request_reset` y `token_from_email` (el token se saca del enlace del correo, como lo haría quien lo abre).
- **Nombres:** cada prueba lleva el ID de su caso (`test_tok_l1_…`, `test_upd_x3_…`), así se localiza desde las tablas de este documento.

## Revisión asistida por IA

Con el borrador de casos hecho, se hizo una pasada específica con el agente de IA (Claude Code): revisar la lógica de `core/security.py`, `auth/passwords.py`, `auth/dependencies.py`, `users/service.py` y los routers, y proponer casos que faltaran. El desarrollador revisó cada propuesta antes de incluirla. La IA también generó el código de las pruebas a partir de estas tablas; el desarrollador revisó cada fase antes de su commit.

**Casos que propuso y se añadieron (marcados con IA):**
- TOK-L3 (revocación en el mismo segundo);
- TOK-X3 (`alg: none`);
- LOG-L3 (contraseña de más de 72 bytes);
- LOG-X3 (cuenta desactivada con contraseña incorrecta);
- VAL-X2 (enlace de otro usuario);
- UPD-X3 (cambio de contraseña por `PUT /users/{id}`);
- GPR-L1 (`manager` frente a admin).

**Posibles fallos que señaló.** Si una prueba los confirma, se consultan antes de corregirlos y se documentan en "Bugs encontrados".

- **H-1. `PUT /users/{id}` con `password` no cierra las sesiones anteriores.** `users/service.py` (`update_user`) guarda el hash nuevo, pero no `password_changed_at`, y no anula los enlaces de restablecimiento pendientes. `change-password` y `reset-password` sí hacen las dos cosas. Si se confirma, quien cambie su contraseña por esta ruta para echar a un intruso no lo conseguiría. **Confirmado y corregido** (ver "Bugs encontrados").
- **H-2. Error engañoso en `change-password` si la cuenta se borra durante el cambio.** `passwords.change_password` responde "la contraseña actual no es correcta" (400) y anula los enlaces antes de comprobar que el usuario sigue existiendo. Requiere una carrera entre peticiones: es poco probable, pero el mensaje sería falso. **Confirmado y corregido** (ver "Bugs encontrados").

## Bugs encontrados

### H-1. Cambiar la contraseña por `PUT /users/{id}` no cierra las sesiones anteriores

- **Estado:** corregido el 2026-11-10, con la aprobación del desarrollador.
- **Cómo se encontró:** hipótesis de la revisión asistida por IA, confirmada por la prueba UPD-X3 (`tests/auth/test_update_user.py`): después del cambio, un token emitido antes sigue abriendo sesión.
- **Causa:** `users/service.update_user` guarda el hash nuevo, pero no `password_changed_at`, y no anula los enlaces de restablecimiento pendientes. `change-password` y `reset-password` sí hacen las dos cosas.
- **Impacto:** medio. Quien cambie su contraseña por esta ruta para echar a un intruso no lo consigue; un enlace de restablecimiento pedido antes también sigue sirviendo. El backoffice usa `change-password`, así que solo afecta a las llamadas directas a la API.
- **Corrección:** si llega `password`, `update_user` guarda también `password_changed_at` (en segundos enteros, como `iat`) y anula los enlaces pendientes dentro del mismo bloqueo, como `change-password`. La respuesta no trae un token nuevo: quien cambie su propia contraseña por esta ruta tiene que volver a iniciar sesión (salvo que su token se emitiera en el mismo segundo). Una actualización sin `password` no toca sesiones ni enlaces.
- **Pruebas de regresión:** los tres casos UPD-X3 (`tests/auth/test_update_user.py`): cambio propio, cambio de un admin sobre otra cuenta y cambio sin contraseña. Los dos primeros fallan sin la corrección y pasan con ella. Mientras se decidía, UPD-X3 estuvo marcada como `xfail` estricta.

### H-2. `change-password` decía que la contraseña actual era incorrecta cuando la cuenta ya no existía

- **Estado:** corregido el 2026-11-10, con la aprobación del desarrollador.
- **Cómo se encontró:** hipótesis de la revisión asistida por IA, confirmada con una prueba manual sobre una base temporal: con la contraseña actual correcta, si la cuenta se borraba entre la autenticación (`get_current_user`) y el cambio, la API respondía 400 `invalid_current_password`.
- **Causa:** `passwords.change_password` interpretaba una actualización fallida (`None`, porque el usuario ya no existe) como una contraseña incorrecta. Además, anulaba los enlaces de restablecimiento antes de comprobarlo.
- **Corrección:** una excepción nueva, `AccountGoneError`, que se lanza dentro del bloqueo y antes de tocar los enlaces. La ruta la traduce a 401 `invalid_token`, que es lo que responde `get_current_user` al token de un usuario borrado; el backoffice cierra la sesión ante un 401. Una contraseña actual incorrecta sigue siendo 400 `invalid_current_password`.
- **Prueba de regresión:** CHG-X2 (`tests/auth/test_change_password.py`). Falla sin la corrección y pasa con ella.
- **Impacto:** bajo. Requiere que coincidan dos peticiones (borrar la cuenta y cambiar su contraseña), pero el mensaje era falso y podía llevar a reintentar una contraseña que era correcta.

## API-042: proveedores y gestor de incidencias

> **Estado (2026-11-10): completado.** Ticket extra API-042: dos grupos de endpoints del backoffice distintos de la autenticación, con la misma estructura de tres niveles y al menos un 60 % de cobertura en los módulos probados. El plan de casos se revisó antes de escribir las pruebas. Son 11 módulos y 101 casos; con ellos solos, la cobertura de los dos dominios es del **84 %** (ver "Cobertura").

- **Grupos (decisión E-1):** el directorio de proveedores (6 endpoints, `tests/suppliers/`) y el gestor de incidencias (5 endpoints, `tests/incidents/`). El analizador del CSV (`/incidents/analyze` y `/results/export`) queda fuera.
- **Cómo (E-2):** un módulo por endpoint que llama a la función de la ruta con un repositorio TinyDB temporal, sin HTTP, como `tests/auth/`. Las pruebas de router que ya existían se movieron a `tests/integration/` (E-3).
- **Qué se afirma:** el `ApiError` (estado y código), lo guardado en la base y las reglas de los modelos del briefing. La validación que hace FastAPI de los parámetros (por ejemplo, un `?country=` no válido) es HTTP: la cubren las pruebas de integración; aquí se prueba la regla, es decir, que el valor no está en el enum del briefing.
- **Tiempo:** `updated_at` se controla sustituyendo el reloj del repositorio de proveedores (fixture `clock`, que fija `utc_now`) o con el parámetro `now` del de incidencias, nunca con esperas.
- **Fixtures:** `repository` y `add_supplier` (`tests/suppliers/conftest.py`), y `repository` y `add_incident` (`tests/incidents/conftest.py`), que lleva la incidencia a un estado por transiciones válidas. Datos válidos de partida en `supplier_data` e `incident_data` (`helpers.py` de cada carpeta). `raises_api_error` se movió a `tests/helpers.py`, compartido por las tres baterías.
- **Cobertura (E-4):** solo con `tests/suppliers/` y `tests/incidents/`, sobre los dominios `suppliers` e `incidents`. Se dan también la cifra sin HTTP y la completa.

### `tests/suppliers/` — directorio de proveedores

#### `test_create_supplier.py` — `POST /suppliers`

| ID | Caso | Decisión esperada | Por qué |
|---|---|---|---|
| CSU-F1 | Proveedor válido de Colombia en COP | Se guarda con ID asignado y `updated_at`; el nombre y las notas se guardan sin espacios extremos; `GET` lo devuelve igual | |
| CSU-L1 | Tarifa mínima positiva (`0.01`), una sola categoría y `notes` vacío | Se acepta; `notes` vacío se guarda como `null` | Límites del modelo |
| CSU-L2 | Nombre ya registrado con otra capitalización o con espacios | 409 `duplicate_supplier` y no se crea nada | El nombre identifica al proveedor |
| CSU-X1 | País y moneda que no coinciden (Colombia con USD, USA con COP) | Lo rechaza el modelo | Regla de negocio del briefing |
| CSU-X2 | Tarifa 0, negativa, como texto (`"10"`), NaN o infinita; categorías repetidas o lista vacía; `id` o `updated_at` en la entrada | Lo rechaza el modelo | Los genera el sistema; la tarifa es estricta |

#### `test_list_suppliers.py` — `GET /suppliers`

| ID | Caso | Decisión esperada |
|---|---|---|
| LSU-F1 | Sin filtros | Todos, ordenados por ID |
| LSU-L1 | Filtros combinados (`country` + `category`); proveedor con varias categorías; filtro sin coincidencias; base vacía | Solo los que cumplen los dos; el de varias categorías aparece por cualquiera de ellas; lista vacía sin error |
| LSU-X1 | País o categoría que no están en el briefing (`México`, `pescado`) | Los rechazan los enums `Country` y `Category` |

#### `test_get_supplier.py` — `GET /suppliers/{id}`

| ID | Caso | Decisión esperada |
|---|---|---|
| GSU-F1 | ID existente | El proveedor |
| GSU-L1 | ID 0 o negativo | 404 `supplier_not_found`, sin error interno |
| GSU-X1 | ID inexistente o de un proveedor borrado | 404 `supplier_not_found` |

#### `test_update_supplier_rate.py` — `PATCH /suppliers/{id}/rate`

| ID | Caso | Decisión esperada | Por qué |
|---|---|---|---|
| RSU-F1 | Tarifa nueva | Cambia la tarifa y `updated_at` pasa al instante del cambio; el resto no cambia | Auditoría de precios del briefing |
| RSU-L1 | La misma tarifa que ya tenía | Se acepta y `updated_at` se actualiza igualmente | Documenta la decisión actual: cada cambio registrado es un evento |
| RSU-X1 | Tarifa 0, negativa o como texto; campo extra | Lo rechaza `RateUpdate` | |
| RSU-X2 | ID inexistente | 404 `supplier_not_found` y no se crea nada | |

#### `test_update_supplier_status.py` — `PATCH /suppliers/{id}/status`

| ID | Caso | Decisión esperada | Por qué |
|---|---|---|---|
| SSU-F1 | `active` → `suspended` | Cambia el estado y **no** cambia `updated_at` | `updated_at` es la fecha de la última tarifa |
| SSU-L1 | Reactivar (`suspended` → `active`); poner el estado que ya tiene | Se aceptan | No hay ciclo de vida: los dos estados van y vuelven |
| SSU-X1 | Estado fuera del briefing (`inactive`, `ACTIVE`) | Lo rechaza `StatusUpdate` | |
| SSU-X2 | ID inexistente | 404 `supplier_not_found` | |

#### `test_delete_supplier.py` — `DELETE /suppliers/{id}`

| ID | Caso | Decisión esperada | Por qué |
|---|---|---|---|
| DSU-F1 | ID existente | Devuelve el proveedor y desaparece de la lista y del detalle | |
| DSU-L1 | Crear de nuevo un proveedor con el nombre del borrado | Se acepta | El nombre queda libre |
| DSU-X1 | ID inexistente; borrar dos veces | 404 `supplier_not_found`; la segunda vez, también | |

### `tests/incidents/` — gestor de incidencias

#### `test_create_incident.py` — `POST /incidents`

| ID | Caso | Decisión esperada | Por qué |
|---|---|---|---|
| CIN-F1 | Incidencia válida sin `status` | Se guarda en `open`, con ID y `created_at` igual a `updated_at`; título y descripción sin espacios extremos | Toda incidencia nueva empieza abierta |
| CIN-L1 | Título de 120 caracteres y descripción de 2000; uno más en cada uno | Los primeros se aceptan; los segundos, no | Límites del modelo |
| CIN-L2 | `status: "open"` explícito | Se acepta | |
| CIN-X1 | `status` distinto de `open` | Lo rechaza el modelo | El estado cambia después, por su ruta |
| CIN-X2 | Categoría, origen o sede fuera del briefing; valores del sistema legacy (`CUSTOMER_COMPLAINT`); título solo con espacios; `id` o `created_at` en la entrada | Lo rechaza el modelo | Los valores son exactamente los del briefing |

#### `test_list_incidents.py` — `GET /incidents`

| ID | Caso | Decisión esperada |
|---|---|---|
| LIN-F1 | Sin filtros | Todas, de la más reciente a la más antigua |
| LIN-L1 | Dos incidencias en el mismo instante; los cuatro filtros combinados; base vacía | El empate se ordena por ID descendente; solo las que cumplen todos los filtros; lista vacía sin error |
| LIN-X1 | Filtros con valores fuera del briefing o del legacy (`OPEN`, `closed`) | Los rechazan los enums del modelo |

#### `test_incident_summary.py` — `GET /incidents/summary`

| ID | Caso | Decisión esperada | Por qué |
|---|---|---|---|
| SIN-F1 | Varias incidencias | Total y recuento por estado, categoría, origen y sede | |
| SIN-L1 | Base vacía | `total` 0 y **todos** los valores del briefing presentes, en 0 | El panel no debe romperse por una clave ausente |
| SIN-X1 | Tras cambiar estados | Cuenta cada incidencia en su estado actual, una sola vez | Un resumen desfasado daría totales falsos |

#### `test_get_incident.py` — `GET /incidents/{id}`

| ID | Caso | Decisión esperada |
|---|---|---|
| GIN-F1 | ID existente | La incidencia |
| GIN-L1 | ID 0 o negativo | 404 `incident_not_found`, sin error interno |
| GIN-X1 | ID inexistente | 404 `incident_not_found` |

#### `test_update_incident_status.py` — `PATCH /incidents/{id}/status`

| ID | Caso | Decisión esperada | Por qué |
|---|---|---|---|
| UIN-F1 | `open` → `in_progress` → `resolved` | Cada paso cambia el estado y `updated_at`; `created_at` no cambia | Ciclo de vida del briefing |
| UIN-L1 | Las cuatro transiciones permitidas, incluido descartar desde `open` y desde `in_progress` | Se aceptan | |
| UIN-X1 | Transiciones no permitidas (`open` → `resolved`, volver a `open`, el mismo estado) | 400 `invalid_transition` con las opciones válidas; el estado no cambia | |
| UIN-X2 | Desde un estado final (`resolved`, `discarded`) | 400 `invalid_transition` con el mensaje de estado final | |
| UIN-X3 | ID inexistente; estado fuera del briefing | 404 `incident_not_found`; lo rechaza `StatusUpdate` | |

## Pruebas del backoffice (Jest)

Cubren la lógica TypeScript de autenticación de `uis/backoffice`. El frontend no genera tokens ni calcula hashes (eso vive en la API), así que lo probado son sus utilidades de autenticación. Cada función tiene al menos un caso feliz y uno de fallo.

- **Configuración:** `jest.config.js` (en `.js` para no necesitar `ts-node`), con ts-jest y el alias `@/`. El entorno es `node`; `token.test.ts` y `navigation.test.ts` piden `jsdom` en su cabecera porque usan `localStorage` y `window`.

| Archivo | Funciones | Casos destacados |
|---|---|---|
| `validation.test.ts` | `validateLogin`, `emailError`, `passwordError`, `validateRegister`, `validateNewPassword`, `validateChangePassword`, `mergeFieldErrors` | Mismos límites que la API (8 caracteres y 72 bytes, con acentos); confirmación distinta; un error de la API borrado no tapa el local (regresión de AUTH-03) |
| `navigation.test.ts` | `safeNext`, `loginUrl`, `currentPath` | Redirecciones abiertas rechazadas: `https://…`, `//…`, `/\…`, `javascript:` y rutas relativas |
| `token.test.ts` | `getToken`, `setToken`, `clearToken`, `subscribeToToken` | `localStorage` bloqueado: sin sesión al leer, `TokenStorageError` al guardar y sin error al borrar; avisos de cambio en esta pestaña y en otras |
| `api-errors.test.ts` | `formErrorsFromApi`, `errorFromStatus` | Detalles de un 422 por campo; 409 de email duplicado junto al email; un error técnico nunca se muestra; un 5xx nunca muestra detalles |

## Cobertura

Medida el 2026-11-10. "Módulos de autenticación" son `core/security.py`, `domains/auth/`, `domains/users/` y `domains/profiles/` (762 sentencias).

| Batería | Pruebas | Cobertura de auth |
|---|---|---|
| **Solo `tests/auth/`** (objetivo del 70 %) | 146 | **88 %** (94 sentencias sin cubrir) |
| Completa (`uv run pytest`) | 705 | 98 % |
| Punto de partida, sin pruebas HTTP (antes de AUTH-088) | 255 | 75 % |

Con toda la batería, `uv run pytest --cov` da un **98 %** de toda `app/` (1596 sentencias).

**Detalle con solo `tests/auth/`:**

| Módulo | Cobertura | Qué queda sin cubrir y por qué |
|---|---|---|
| `users/router.py`, `users/service.py`, `profiles/router.py`, `auth/dependencies.py`, modelos y repositorios | 100 % | — |
| `auth/passwords.py` | 99 % | Una comprobación defensiva de `reset_password`: el usuario ya se comprueba dentro del mismo bloqueo |
| `core/security.py` | 97 % | Dos comprobaciones de claims que solo fallarían con un token firmado con la clave de la API pero mal construido (`iat` no entero; enlace con `jti` y sin `purpose`) |
| `auth/router.py` | 80 % | `read_credentials`: lee el cuerpo JSON o de formulario del login. Es HTTP; lo cubren las pruebas de integración |
| `users/database.py` y `users/dependencies.py` | 93 % y 56 % | La apertura de la base real y su inyección: las pruebas usan una base temporal |
| `users/create_admin.py` | 0 % | Es el comando de consola `uv run create-admin`, no un endpoint. Lo cubre `tests/domains/users/test_create_admin.py` |

**API-042** (solo `tests/suppliers/` y `tests/incidents/`, sobre los dominios `suppliers` e `incidents`, 579 sentencias):

| Batería | Pruebas | Cobertura |
|---|---|---|
| **Solo los módulos de API-042** (objetivo del 60 %) | 101 | **84 %** |
| Sin pruebas HTTP (`-m "not integration"`) | 502 | 91 % |
| Completa | 806 | 98 % |
| Punto de partida, sin las pruebas de router (antes de API-042) | 118 | 86 % |

| Módulo | Cobertura | Qué queda sin cubrir y por qué |
|---|---|---|
| `suppliers/router.py`, `incidents/manager_router.py` y los modelos de los dos | 100 % | — |
| `suppliers/repository.py` | 95 % | `find_by_name` e `is_empty`, que usa el seed |
| `incidents/incident_repository.py` | 90 % | `is_seeded` y `create_from_seed`, que usa la carga del CSV histórico |
| `suppliers/seed.py` | 36 % | El comando `uv run seed`; lo cubre `tests/domains/suppliers/test_supplier_seed.py` |
| `incidents/router.py`, `repository.py`, `schemas.py` y `service.py` | 33–100 % | El analizador del CSV, fuera de API-042 (decisión E-1); lo cubren `tests/integration/test_incident_analyzer_router.py` y `tests/domains/incidents/` |
| `dependencies.py` de los dos | 60–64 % | La apertura de la base real; las pruebas usan una temporal |

**Jest** (`npm run test:coverage`):

| Archivo | Sentencias | Líneas |
|---|---|---|
| `lib/auth/validation.ts` | 100 % | 100 % |
| `lib/auth/api-errors.ts` | 100 % | 100 % |
| `lib/auth/navigation.ts` | 94 % | 100 % |
| `lib/auth/token.ts` | 90 % | 97 % |
| **`lib/auth/` en total** | **96 %** | **99 %** |
| `lib/api-client.ts` | 40 % | 45 % |

De `api-client.ts` solo entra en AUTH-088 `errorFromStatus`: `apiFetch` necesitaría simular `fetch` y la redirección del navegador, y `readJson` queda para el extra FE-019.
