# Pruebas de la API de Brasaland

> **Estado (2026-11-10): plan de pruebas.** Este documento lista los casos que se van a cubrir antes de escribir ninguna prueba (ticket AUTH-088). Las secciones de ejecución, cobertura y resultados se completan al terminar la batería.

> _Versión en inglés: [TESTING.md](./TESTING.md)._

## Suites

| Suite | Carpeta | Qué comprueba |
|---|---|---|
| **Unitarias de autenticación** (AUTH-088) | `tests/auth/` | La lógica de cada endpoint de autenticación: qué decide, no cómo responde. Llaman directamente a las funciones de cada ruta y a sus servicios, sin cliente HTTP. *Por crear.* |
| **Integración HTTP** | `tests/integration/` | El contrato HTTP con el backoffice: rutas protegidas, códigos de estado, formato `{"error": {...}}` y cabeceras. Son las pruebas de router que ya existían. Llevan el marker `integration`. *Se moverán en la Fase 2.* |
| **Resto** | `tests/core/` y `tests/domains/` | Configuración, seguridad, correo, errores, repositorios y los dominios `incidents` y `suppliers`. |

## Cómo ejecutarlas

*Preliminar; se confirma al terminar.* Desde `services/brasaland-api/`:

```bash
uv sync --extra dev                      # instala pytest, pytest-cov y httpx
uv run pytest                            # toda la batería
uv run pytest tests/auth                 # solo las unitarias de autenticación
uv run pytest -m "not integration"       # todo menos las pruebas HTTP
uv run pytest --cov                      # toda la batería con cobertura
```

## Criterios del plan

- **Lógica, no HTTP.** Cada prueba afirma una decisión de la aplicación: qué token se emite, qué `ApiError` se lanza y con qué código, qué queda guardado en la base. No se comprueba el JSON, los códigos que pone FastAPI ni la validación del cuerpo por el framework. Las reglas de nuestros modelos (longitud de contraseña, campos prohibidos) sí se prueban, porque son reglas de negocio.
- **Sin HTTP ni red.** Las pruebas usan una base TinyDB temporal y el emisor de correo falso (`tests/conftest.py`). El tiempo se controla con los parámetros `now` y `expires_delta` de la lógica, nunca con esperas.
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
| UPD-X3 **(IA)** | Un usuario cambia su contraseña por esta ruta | **A comprobar:** ¿se cierran las sesiones anteriores, como en AUTH-03? | Ver la hipótesis H-1 |

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

## Revisión asistida por IA

Con el borrador de casos hecho, se hizo una pasada específica con el agente de IA (Claude Code): revisar la lógica de `core/security.py`, `auth/passwords.py`, `auth/dependencies.py`, `users/service.py` y los routers, y proponer casos que faltaran. El desarrollador revisó cada propuesta antes de incluirla.

**Casos que propuso y se añadieron (marcados con IA):**
- TOK-L3 (revocación en el mismo segundo);
- TOK-X3 (`alg: none`);
- LOG-L3 (contraseña de más de 72 bytes);
- LOG-X3 (cuenta desactivada con contraseña incorrecta);
- VAL-X2 (enlace de otro usuario);
- UPD-X3 (cambio de contraseña por `PUT /users/{id}`);
- GPR-L1 (`manager` frente a admin).

**Posibles fallos que señaló.** Están sin confirmar. Si una prueba los confirma, se consultan antes de corregirlos y se documentan en "Bugs encontrados".

- **H-1. `PUT /users/{id}` con `password` no cierra las sesiones anteriores.** `users/service.py` (`update_user`) guarda el hash nuevo, pero no `password_changed_at`, y no anula los enlaces de restablecimiento pendientes. `change-password` y `reset-password` sí hacen las dos cosas. Si se confirma, quien cambie su contraseña por esta ruta para echar a un intruso no lo conseguiría.
- **H-2. Error engañoso en `change-password` si la cuenta se borra durante el cambio.** `passwords.change_password` responde "la contraseña actual no es correcta" (400) y anula los enlaces antes de comprobar que el usuario sigue existiendo. Requiere una carrera entre peticiones: es poco probable, pero el mensaje sería falso.

## Bugs encontrados

*Ninguno por ahora.*

## Cobertura

*Pendiente.* Cobertura de partida de los módulos de autenticación (`core/security.py`, `domains/auth`, `domains/users` y `domains/profiles`), medida el 2026-11-10:

| Batería | Cobertura |
|---|---|
| Completa (`uv run pytest --cov`) | 98 % |
| Sin pruebas HTTP | 75 % |

El objetivo de AUTH-088 es un 70 % o más **solo con `tests/auth/`**.
