# Propuesta de arquitectura del backend — Brasaland

> **Para:** Nicolás Park (CTO) y equipo Brasaland Digital
> **Estado:** borrador para revisión
> **Fecha:** 2026-10-28

---

## 1. Patrón arquitectónico

### 1.1 Recomendación

Propongo una **arquitectura en capas organizada por dominio de negocio**, con una excepción deliberada: las **integraciones con sistemas externos** (POS, tipo de cambio, proveedor de IA, correo) se aíslan detrás de interfaces propias, tomando de la arquitectura hexagonal solo la idea de puertos y adaptadores.

Descarto MVC y serverless como base, y descarto aplicar la arquitectura hexagonal a todo el sistema. Las secciones siguientes explican por qué, a partir de las características concretas de Brasaland.

### 1.2 Características de Brasaland que condicionan la decisión

| Característica | Qué le exige a la arquitectura |
|---|---|
| **Equipo pequeño construyendo desde casi cero.** No hay API interna, datos consolidados ni telemetría. | Una estructura que cualquiera entienda sin formación especial y que permita entregar endpoints útiles pronto. |
| **Las interfaces ya existen o existirán por separado:** el tracker de candidatos en Next.js, la web corporativa, la futura app de fidelización, el backoffice y los agentes de IA. | El backend no genera pantallas: expone una API JSON que consumen varios clientes distintos. |
| **Reglas que cambian según el país:** dos monedas (COP y USD), dos legislaciones laborales, dos zonas horarias y dos idiomas. | Un lugar único y comprobable para las reglas de negocio, fuera de los endpoints y de la base de datos. |
| **Muchos dominios con lógica mayoritariamente de registro y consulta:** candidatos, recetas, proveedores, locales y menús. | No imponer abstracciones pesadas donde la lógica es simple. |
| **Integraciones externas que van a cambiar:** un POS distinto en cada país, una tasa de cambio que hoy es fija (1 USD = 4000 COP) pero no lo será siempre, un proveedor de LLM para el asistente de dirección y el envío del informe semanal. | Poder sustituir o añadir una integración sin tocar las reglas de negocio. |
| **Procesos continuos y programados:** alertas cuando un local no registra ventas en horario de apertura, telemetría en tiempo real e informe automático cada lunes a las 7:00. | Soportar conexiones persistentes y tareas de fondo, no solo peticiones aisladas. |
| **Volumen modesto y previsible:** 14 locales y unas 115 personas. | Escalar no es el problema principal; la prioridad es la claridad y la consistencia de los datos. |

### 1.3 Evaluación de las alternativas

#### MVC (Modelo–Vista–Controlador)

MVC separa los datos (modelo), la presentación (vista) y la coordinación entre ambos (controlador). Nació para aplicaciones que generan la interfaz en el servidor.

- **En Brasaland, la vista no está en el backend.** Las pantallas viven en Next.js y en la web estática; la API solo devuelve JSON. De MVC quedan el modelo y el controlador, y el patrón no indica dónde van las reglas de negocio.
- **En la práctica, las reglas acaban en los controladores o en los modelos del ORM.** Con reglas distintas por país, que se repetirían en ventas, compras, RRHH y dashboards, eso las dispersa por decenas de endpoints.
- **Lo útil de MVC ya está cubierto.** La separación entre presentación y lógica se consigue al tener frontend y backend como sistemas separados.

**Veredicto:** descartado como patrón del backend.

#### Arquitectura en capas

Organiza el código en niveles con responsabilidades distintas: **API** (endpoints y validación de entrada y salida), **servicios** (reglas de negocio) y **datos** (acceso a la base de datos). Cada capa solo usa la inmediatamente inferior.

A favor, en el contexto de Brasaland:

- **Encaja con FastAPI sin esfuerzo.** Los routers y los esquemas Pydantic forman la capa API; las dependencias de FastAPI conectan con los servicios.
- **Da un único lugar a las reglas por país.** La conversión de moneda, la hora local de cada restaurante o las reglas laborales viven en la capa de servicios y las reutilizan todos los endpoints y clientes.
- **Las reglas se pueden probar sin levantar la API.** Eso importa cuando un error de cálculo en el ticket promedio o en una conversión llega directamente al dashboard de dirección.
- **Es el patrón más conocido.** Reduce el tiempo de incorporación de cualquier miembro del equipo.

En contra, y cómo se mitiga:

- **Si las capas se aplican a todo el proyecto a la vez** (una carpeta con todos los endpoints, otra con todos los servicios), los dominios se mezclan y cuesta saber qué pertenece a qué. Por eso propongo aplicarlas **dentro de cada dominio**; la organización de módulos se detalla en la sección 2.
- **En los dominios simples, alguna capa solo pasa datos** de un nivel a otro sin añadir lógica. Es un coste pequeño que se acepta a cambio de una estructura uniforme.
- **La capa de servicios tiende a acoplarse a lo que está debajo.** Para las integraciones externas eso es un problema; de ahí la excepción del apartado 1.4.

**Veredicto:** elegido como patrón base.

#### Serverless

La lógica se despliega como funciones independientes que un proveedor cloud ejecuta bajo demanda.

A favor:

- Ningún servidor que mantener y, con poco tráfico, pago por uso.
- Encaja con tareas aisladas como generar y enviar el informe del lunes.

En contra:

- **No encaja con el tiempo real.** La telemetría, el dashboard en vivo y la vigilancia de locales sin ventas necesitan procesos continuos y conexiones persistentes, justo lo que peor resuelve este modelo.
- **Ata al proveedor cloud antes de tiempo.** Todavía no hay infraestructura ni hosting decididos.
- **Complica la base de datos relacional** con arranques en frío y conexiones abiertas desde muchas funciones.
- **Fragmenta la lógica** en funciones sueltas, más difíciles de seguir, depurar y probar en local para un equipo pequeño.
- **Es un modelo de despliegue, no de organización del código.** Aunque se adoptara, seguiría haciendo falta decidir cómo se estructuran las reglas de negocio.

**Veredicto:** descartado como base. Se puede reconsiderar para tareas programadas concretas cuando exista infraestructura.

#### Arquitectura hexagonal (puertos y adaptadores)

Coloca las reglas de negocio en un núcleo que no conoce la base de datos, ni HTTP, ni ningún proveedor. Se comunica con el exterior mediante interfaces propias (puertos) y sus implementaciones (adaptadores).

A favor:

- **Brasaland tiene un caso de manual:** dos POS distintos, uno por país, cuyas ventas deben llegar al sistema con el mismo formato. Con un adaptador por POS, las reglas de ventas no saben de qué terminal vienen los datos.
- **Lo mismo vale para el resto de integraciones.** La tasa de cambio, el LLM del asistente y el envío de correo se pueden cambiar de proveedor sin tocar el núcleo.

En contra:

- **Aplicada a todo el sistema**, cada dominio necesita interfaces, adaptadores y conversiones entre los modelos del núcleo y los de la base de datos. En dominios como candidatos, recetas o proveedores, de lógica mayoritariamente simple, eso multiplica los archivos sin aportar valor.
- **Exige experiencia en el patrón** y ralentiza las primeras entregas, justo cuando el objetivo es que la API central empiece a dar servicio.

**Veredicto:** no como arquitectura global. Sí se aplica su idea en los puntos de integración externa.

### 1.4 Decisión

**Arquitectura en capas dentro de cada dominio, con adaptadores para las integraciones externas.**

```
   Clientes: Next.js (backoffice, tracker), web, app de fidelización, agentes de IA
                                   │  HTTP / JSON
  ┌────────────────────────────────▼──────────────────────────────┐
  │ API        endpoints y esquemas de entrada y salida            │
  ├───────────────────────────────────────────────────────────────┤
  │ Servicios  reglas de negocio (país, moneda, hora local, roles) │──▶ Interfaces propias
  ├───────────────────────────────────────────────────────────────┤        │
  │ Datos      modelos y consultas a la base de datos              │        ▼
  └────────────────────────────────┬──────────────────────────────┘    Adaptadores:
                                   ▼                                   POS Colombia · POS Florida
                             Base de datos                             tipo de cambio · LLM · correo
```

Reglas que se derivan de esta decisión:

1. **Los endpoints no contienen reglas de negocio.** Validan la entrada y la salida y delegan en un servicio.
2. **Las reglas de negocio, incluidas las que dependen del país, viven solo en la capa de servicios.**
3. **Solo la capa de datos accede a la base de datos.**
4. **Las dependencias apuntan siempre hacia abajo:** un servicio nunca importa un endpoint, y los datos nunca llaman a un servicio.
5. **Toda integración externa se usa a través de una interfaz definida por nosotros.** Un servicio no importa el SDK de un POS, de un banco ni de un proveedor de IA.

### 1.5 Consecuencias

**Lo que ganamos:**

- Un patrón que el equipo puede adoptar desde el primer endpoint, sin formación previa.
- Las reglas sensibles para el negocio (dinero, horarios, legislación) quedan en un solo sitio y se pueden probar.
- Cambiar de POS, pasar a una tasa de cambio variable o cambiar de proveedor de IA afecta a un adaptador, no a los dominios.
- Al estar organizado por dominios, un módulo que llegue a necesitar escalar por separado (por ejemplo, la ingesta de telemetría) se puede extraer después sin rehacer el resto.

**Lo que aceptamos:**

- Algo de código repetitivo en los dominios simples.
- **La separación depende de la disciplina del equipo.** FastAPI no impide saltarse capas, así que las reglas del apartado 1.4 tienen que vigilarse activamente (ver 6.4).

**Cuándo revisaríamos esta decisión:**

- Si un dominio concreto (previsiblemente ventas o inventario) acumula lógica compleja, se puede aplicar la arquitectura hexagonal completa solo a ese dominio.
- Si un proceso necesita escalar o desplegarse por separado, se extrae como servicio o worker independiente.

---

## 2. Estructura de carpetas y módulos

### 2.1 Criterio de separación

El backend se organiza en **dos niveles**, cada uno con un criterio distinto:

1. **Primer nivel: por dominio de negocio.** Cada carpeta representa una parte del negocio de Brasaland (recetas, ventas, inventario, fidelización…), no un tipo de archivo.
2. **Segundo nivel: por responsabilidad.** Dentro de cada dominio se aplican las capas de la sección 1: endpoints, reglas de negocio y acceso a datos.

**Por qué el dominio va primero.** Un cambio real en Brasaland casi siempre afecta a una sola área del negocio. Si Jake Morrison pide que las recetas tengan versiones, el cambio debe quedar dentro de `recipes/`, no repartido entre una carpeta de endpoints, otra de servicios y otra de modelos compartidas por todo el sistema. Organizar por dominio también:

- Permite repartir el trabajo del equipo por áreas sin pisarse.
- Hace visible quién es dueño de cada dato.
- Deja cada dominio listo para extraerse como servicio independiente si algún día lo necesita (sección 1.5).

**Qué convierte algo en un dominio.** Una parte del sistema merece su propio módulo cuando cumple la mayoría de estas condiciones:

- Tiene **vocabulario propio**: "merma", "stock mínimo" y "pedido" pertenecen a inventario; "puntos" y "canje", a fidelización.
- Tiene **datos propios** de los que es la única fuente de verdad.
- Tiene **reglas propias** que cambian por motivos distintos a las de otros módulos.
- Tiene un **responsable de negocio** identificable en la empresa.

Si algo no cumple estas condiciones, no es un dominio: es código compartido (`core/`) o una integración externa (`integrations/`).

### 2.2 Ubicación en el monorepo

El backend es un único servicio en `services/brasaland-api/`, siguiendo la convención del monorepo de una carpeta por servicio dentro de `services/`. Los frontends (`uis/`) y los agentes de IA (`agents/`) son clientes de esta API; cómo se relacionan con ella se describe en la sección 5.

Los nombres de carpetas, archivos y código van en **inglés**, igual que en el frontend actual. La documentación y los comentarios siguen en español.

### 2.3 Estructura propuesta

```
services/brasaland-api/
├── app/
│   ├── main.py                 # Crea la aplicación y registra los routers de cada dominio
│   │
│   ├── core/                   # Código transversal, sin reglas de ningún dominio
│   │   ├── config.py           # Configuración por entorno
│   │   ├── database.py         # Conexión y sesión de base de datos
│   │   ├── security.py         # Autenticación y comprobación de permisos
│   │   ├── errors.py           # Formato único de errores de la API
│   │   ├── pagination.py       # Formato único de listados paginados
│   │   ├── money.py            # Importes con moneda (COP / USD)
│   │   └── timezones.py        # Hora local de cada país y conversión desde UTC
│   │
│   ├── domains/
│   │   ├── auth/               # Usuarios de la plataforma, roles y acceso por local o país
│   │   ├── locations/          # Locales: país, ciudad, moneda, zona horaria, horario
│   │   ├── menu/               # Productos que se venden y sus precios por país
│   │   ├── recipes/            # Recetas, versiones, traducciones y publicación a locales
│   │   ├── training/           # Itinerarios de incorporación y progreso por estación
│   │   ├── sales/              # Ventas normalizadas desde los POS de cada país
│   │   ├── inventory/          # Stock por local, mermas y pedidos de ingredientes
│   │   ├── procurement/        # Proveedores, historial de precios y compras
│   │   ├── customers/          # CRM: clientes, historial y preferencias
│   │   ├── loyalty/            # Brasa Points: acumulación, saldo y canjes
│   │   ├── people/             # Empleados, ausencias, vacaciones y alta administrativa
│   │   ├── recruitment/        # Candidatos y notas (API del talent-pipeline-tracker)
│   │   ├── telemetry/          # Eventos en tiempo real de los locales
│   │   └── reporting/          # Métricas y dashboards (solo lectura)
│   │
│   ├── integrations/           # Adaptadores a sistemas externos (sección 1.4)
│   │   ├── pos/                # Interfaz común + un adaptador por POS (Colombia, Florida)
│   │   ├── exchange_rates/     # Interfaz + adaptador de tasa fija (luego, tasa variable)
│   │   ├── llm/                # Interfaz + adaptador del proveedor de IA
│   │   └── email/              # Interfaz + adaptador de envío de correo
│   │
│   └── jobs/                   # Tareas programadas y de fondo, en un proceso aparte
│       ├── no_sales_alert.py   # Aviso cuando un local abierto no registra ventas
│       ├── loyalty_accrual.py  # Acumulación de Brasa Points a partir de las ventas nuevas
│       └── weekly_report.py    # Informe ejecutivo de los lunes
│
├── migrations/                 # Historial único de cambios del esquema de base de datos
├── tests/                      # Replica la estructura de app/ (tests/domains/recipes/…)
├── pyproject.toml              # Dependencias y configuración de herramientas
├── .env.example                # Variables de entorno necesarias, sin valores reales
├── Dockerfile
└── README.md                   # Cómo instalar, ejecutar y probar el servicio
```

Este árbol es el **mapa de destino**, no lo que se crea el primer día. Cada dominio se añade cuando se empieza a trabajar en él (ver 2.7).

### 2.4 Estructura interna de un dominio

Todos los dominios siguen la misma plantilla. Cada archivo pertenece a una única capa de la sección 1:

```
domains/recipes/
├── router.py        # Capa API:       endpoints del dominio
├── schemas.py       # Capa API:       formatos de entrada y salida (lo que ve el cliente)
├── service.py       # Capa servicios: reglas de negocio del dominio
├── repository.py    # Capa datos:     consultas a la base de datos
├── models.py        # Capa datos:     tablas del dominio
├── dependencies.py  # Piezas reutilizables por los endpoints (p. ej. "la receta existe")
└── exceptions.py    # Errores propios del dominio ("receta no publicada")
```

- **`schemas.py` y `models.py` se separan a propósito.** Lo que la API expone no tiene por qué coincidir con cómo se guarda. Por ejemplo, un empleado tiene datos internos que no deben salir en todas las respuestas, y el cliente no debe poder fijar campos como el identificador o la fecha de creación.
- **Si un dominio no necesita un archivo, no se crea.** `reporting/`, por ejemplo, no tiene tablas propias.
- **Una plantilla única** hace que quien conoce un dominio sepa moverse por cualquier otro.

### 2.5 Cómo se relacionan los dominios

Un único backend con una única base de datos hace muy fácil que los dominios se enreden: basta con importar el modelo de otro módulo y escribir en su tabla. Para evitarlo:

1. **Cada tabla tiene un solo dominio dueño**, y solo ese dominio escribe en ella.
2. **Un dominio solo usa otro a través de su `service.py`.** Nunca importa sus modelos ni su repositorio. Por ejemplo, si `inventory` necesita los productos vendidos ayer, se los pide a `sales.service`; no consulta la tabla de ventas.
3. **Las referencias entre dominios se hacen por identificador.** Una venta guarda el `location_id`, no una copia de los datos del local. Lo mismo ocurre con los ingredientes, que usan tres dominios: su dueño es `inventory` (es lo que se almacena y se pide), y `recipes` y `procurement` los referencian por identificador.
4. **Sin dependencias circulares.** Los dominios base (`auth`, `locations`, `menu`) no dependen de nadie. Los operativos dependen de ellos:

   ```
   auth · locations · menu                        ← dominios base
          ▲
   recipes · training · sales · inventory · procurement
   customers · loyalty · people · recruitment · telemetry
          ▲
   reporting                                      ← solo lee
   ```

5. **`reporting` es la única excepción a la regla 2, y es explícita.** Los dashboards de dirección y operaciones necesitan cruzar ventas, locales, inventario y personas. `reporting` puede **leer** datos de varios dominios mediante consultas de solo lectura, pero **nunca escribe**. Así se evita que cada dominio acabe con su propio endpoint de "métricas" y cálculos divergentes de, por ejemplo, el ticket promedio.

### 2.6 Qué va fuera de los dominios

| Carpeta | Qué contiene | Por qué no es un dominio |
|---|---|---|
| `core/` | Configuración, base de datos, seguridad, errores, paginación, dinero y zonas horarias. | Lo usan todos los dominios y no tiene reglas de una sola área del negocio. `money.py` y `timezones.py` están aquí porque **COP/USD y la hora local afectan a casi todos los dominios**: centralizarlos evita que cada uno resuelva la conversión a su manera. |
| `integrations/` | Una interfaz y sus adaptadores por cada sistema externo. | Son sistemas de terceros. Los dominios usan la interfaz y nunca el SDK del proveedor (sección 1.4). |
| `jobs/` | Procesos programados y de fondo. | Reutilizan los servicios de los dominios, pero se ejecutan como **un proceso aparte del que atiende la API**. Así una tarea lenta (generar el informe semanal) no afecta a los tiempos de respuesta de los endpoints. |
| `migrations/` | Cambios del esquema de base de datos. | Hay una sola base de datos y un solo historial; partirlo por dominio complicaría el orden de los cambios. |

### 2.7 Orden de creación de los módulos

Propuesta inicial, sujeta a las prioridades del sprint:

1. **`core/`, `auth/` y `locations/`.** Todos los demás dominios los necesitan.
2. **`recruitment/`.** Ya existe un frontend que lo consumirá, tras la adaptación descrita en 3.5, así que permite validar la estructura de punta a punta desde el primer sprint.
3. **Las tres áreas prioritarias del proyecto:**
   - Operaciones: `menu/`, `sales/` e `inventory/`.
   - Fidelización: `customers/` y `loyalty/`.
   - Formación: `recipes/` y `training/`.
4. **El resto** (`procurement/`, `people/`, `telemetry/`, `reporting/`) según las prioridades de negocio.

---

## 3. Organización de rutas y routers

### 3.1 Criterio de agrupación

- **Un router por dominio.** Cada dominio de la sección 2 declara sus rutas en su propio `router.py`. `main.py` solo registra esos routers; no define rutas de negocio.
- **Las URLs se nombran por recurso, no por dominio.** El cliente piensa en "proveedores" o "pedidos de ingredientes", no en "procurement". Por eso un dominio puede exponer más de un recurso: `procurement` publica `/suppliers` y `/purchases`.
- **La agrupación por dominio se refleja en las etiquetas (tags) de la documentación.** Cada router usa una etiqueta con el nombre de su dominio, con dos efectos:
  - La documentación automática de la API aparece agrupada por área del negocio.
  - El cliente TypeScript que los frontends generen a partir de la API tendrá un servicio por dominio (`RecipesService`, `SalesService`…), en lugar de tipos escritos a mano.
- **Una sola versión para toda la API.** Todas las rutas de negocio cuelgan de `/api/v1`. Se crea una versión nueva solo ante cambios incompatibles, y nunca por dominio: los frontends no deberían combinar versiones distintas de la misma API.
- **Requisitos comunes en el router, no en cada ruta.** Lo que se aplica a todo un dominio se declara una vez en su router: autenticación obligatoria, roles permitidos o errores habituales. Por ejemplo, todo `/employees` exige un rol de RRHH.

### 3.2 Convenciones de rutas

| Convención | Regla | Motivo |
|---|---|---|
| **Nombres** | Sustantivos en plural y en inglés, con guiones (`/ingredient-orders`). Los campos JSON van en `snake_case`. | Coherencia con el código (sección 2.2) y con el frontend actual, que ya usa `snake_case`. |
| **Anidación** | Como máximo un nivel, y solo cuando el recurso hijo no existe sin el padre: `/candidates/{id}/notes`, `/recipes/{id}/versions`. | Evita URLs largas y frágiles, y deja claro qué pertenece a qué. |
| **Métodos** | `GET` para consultar, `POST` para crear, `PATCH` para modificar parcialmente y `DELETE` para borrar. No se usa `PUT`. | Hoy el tracker debe hacer un `PATCH` extra porque el `PUT` de la API que consume reinicia `status` y `stage` (ver 3.5). |
| **Acciones de negocio** | Una operación que hace algo más que cambiar un campo se expone como un `POST` explícito: `POST /recipes/{id}/versions/{version}/publish`. | Publicar una receta la envía a los 14 locales. Debe ser una acción visible y auditable, no un `PATCH` de un campo `published`. |
| **Listados** | Los mismos parámetros en todos los dominios: `page`, `limit`, `q` (búsqueda) y filtros con nombre del campo (`status`, `location_id`, `from`, `to`). Siempre la misma respuesta: `{ data, meta: { total, page, limit } }`. | Hoy el tracker recibe dos formatos distintos de lista. Un formato único permite un único componente de tabla o paginación en los frontends. |
| **Errores** | El mismo formato en todos los dominios, con un código legible por máquina además del mensaje. | El frontend puede mostrar el error correcto sin interpretar textos. |
| **Valores cerrados** | Los estados y categorías se publican como valores cerrados en la documentación de la API (p. ej. los estados posibles de un candidato). | Hoy el tracker deduce los valores válidos de descripciones de texto. |
| **País y local** | Se filtra con parámetros (`country`, `location_id`). Además, los permisos del usuario restringen automáticamente lo que ve: un supervisor de Medellín solo recibe sus locales aunque no filtre. | La operación es bicountry; la seguridad no puede depender de que el cliente envíe el filtro correcto. |
| **Dinero** | Todo importe va acompañado de su moneda. Los endpoints de informes aceptan `currency=COP\|USD` para devolver los totales convertidos. | Dirección necesita ver la cadena completa en una sola moneda (p. ej. "cuánto vendimos esta semana en Florida"). |
| **Fechas** | Se intercambian en formato ISO 8601 y en UTC. El servidor aplica la zona horaria de cada local cuando el filtro es "un día" de ese local. | Colombia y Florida tienen husos distintos, y Florida cambia de hora en verano. |

### 3.3 Mapa de rutas por dominio

Todas las rutas van precedidas de `/api/v1`. El mapa muestra los recursos principales y no pretende ser exhaustivo; cada dominio lo completa cuando se implemente.

| Dominio (tag) | Rutas | Principales clientes |
|---|---|---|
| **auth** | `POST /auth/token` (inicio de sesión) · `GET /auth/me` (usuario actual y sus permisos) · `GET, POST /users` · `GET, PATCH /users/{id}` (cuentas, roles, locales asignados) | Todos los frontends |
| **locations** | `GET, POST /locations` · `GET, PATCH /locations/{id}` (país, ciudad, moneda, zona horaria, horario de apertura) | Todos |
| **menu** | `GET, POST /menu-items` · `GET, PATCH /menu-items/{id}` (precios y disponibilidad por país) | Web, app de fidelización, backoffice |
| **recipes** | `GET, POST /recipes` (búsqueda por nombre o ingrediente, idioma) · `GET, PATCH /recipes/{id}` · `GET, POST /recipes/{id}/versions` · `POST /recipes/{id}/versions/{version}/publish`. La consulta de una receta acepta `servings` y `units` para ajustar porciones y unidades de medida. | Plataforma de formación |
| **training** | `GET, POST /training-paths` · `GET, PATCH /training-paths/{id}` (itinerarios de incorporación) · `GET, POST /enrollments` (asignación de un empleado a un itinerario) · `GET, POST /enrollments/{id}/progress` (horas y tareas por estación) | Plataforma de formación |
| **sales** | `GET /sales` (por local y rango de fechas) · `GET /sales/{id}` · `POST /sales/imports` (carga de ventas desde un POS) | Backoffice, `reporting`, jobs |
| **inventory** | `GET /ingredients` · `GET /stock` (por local) · `POST /stock/adjustments` · `GET, POST /waste-records` · `GET, POST /ingredient-orders` · `GET, PATCH /ingredient-orders/{id}` · `GET /ingredient-orders/suggestions` (pedido sugerido según ventas históricas y stock) | Backoffice de operaciones |
| **procurement** | `GET, POST /suppliers` · `GET, PATCH /suppliers/{id}` · `GET, POST /suppliers/{id}/prices` (historial de precios) · `GET, POST /purchases` | Backoffice de compras |
| **customers** | `GET, POST /customers` · `GET, PATCH /customers/{id}` · `GET /customers/{id}/orders` (historial) | Backoffice de marketing, app de fidelización |
| **loyalty** | `GET /loyalty/accounts/{customer_id}` (saldo de Brasa Points) · `GET /loyalty/accounts/{customer_id}/transactions` · `POST /loyalty/redemptions` (canje). La acumulación de puntos no tiene endpoint público: la genera el sistema a partir de las ventas. | App de fidelización |
| **people** | `GET, POST /employees` · `GET, PATCH /employees/{id}` · `GET, POST /absences` · `PATCH /absences/{id}` (aprobación o rechazo de vacaciones y ausencias) | Portal de RRHH |
| **recruitment** | `GET, POST /candidates` · `GET, PATCH /candidates/{id}` · `GET, POST /candidates/{id}/notes` · `DELETE /candidates/{id}/notes/{note_id}` | talent-pipeline-tracker |
| **telemetry** | `POST /telemetry/events` (eventos enviados por los locales) · `GET /telemetry/stream` (flujo en tiempo real para el dashboard; tecnología pendiente, ver sección 7) | Locales, dashboard operativo |
| **reporting** | `GET /reports/sales` (por país, local y periodo, en `currency`) · `GET /reports/locations/ranking` (p. ej. ticket promedio por local) · `GET /reports/hr` (rotación, absentismo, cobertura por país) · `GET /reports/executive-summary` | Dashboards, asistente de IA de dirección |

### 3.4 Rutas fuera de los dominios

| Ruta | Para qué | Condiciones |
|---|---|---|
| `GET /health` | Comprobar que el servicio y la base de datos responden. | Fuera de `/api/v1` y sin autenticación, para que la usen la infraestructura y los monitores. |
| `/docs` y `/openapi.json` | Documentación interactiva y contrato de la API, generados automáticamente. | Disponibles en desarrollo y pruebas; en producción, ocultos o protegidos. El contrato es la base para generar el cliente de los frontends. |

`integrations/` y `jobs/` **no exponen rutas propias**. Los jobs llaman directamente a los servicios de los dominios. Las integraciones entran por el dominio al que alimentan; por ejemplo, las ventas de un POS llegan por `POST /sales/imports`, y el adaptador de cada POS las traduce al formato común. Si algún POS solo puede enviar datos mediante avisos automáticos (webhooks), se añadirá una ruta específica dentro de `sales`, sin crear un dominio nuevo.

### 3.5 Transición del talent-pipeline-tracker

El tracker es el único frontend que ya consume una API, y sus tipos documentan los problemas del contrato actual (`uis/talent-pipeline-tracker/types/record.ts`). La nueva API debe resolverlos, no reproducirlos:

| Situación actual | Decisión en la nueva API |
|---|---|
| El recurso se llama `records`, un nombre genérico. | `/candidates`, con el vocabulario del dominio. |
| `status` y `stage` llegan como texto libre; el front deduce los valores válidos. | Valores cerrados publicados en el contrato. |
| `GET /records` responde `{ total, page, limit, data }` y `GET /records/{id}/notes` responde `{ data, meta: { total } }`. | Formato único de listados en toda la API (3.2). |
| `POST` y `PUT` ignoran `status` y `stage`, y el front los corrige con un `PATCH` adicional. | La creación acepta el estado inicial y las modificaciones se hacen con `PATCH`, sin `PUT`. |
| Tipos escritos a mano a partir de pruebas contra la API. | Cliente generado desde el contrato de la API. |

**Consecuencia:** el tracker tendrá que adaptarse, cambiando la URL base, las rutas y los tipos. Es un cambio acotado a `lib/api.ts` y `types/record.ts`. Propongo hacerlo en el mismo sprint en que se implemente `recruitment/`, en lugar de mantener rutas `/records` por compatibilidad: arrastrar el contrato antiguo dejaría a la nueva API con las mismas inconsistencias desde el primer día.

---

## 4. Influencia de las convenciones estándar de FastAPI

Las secciones 2 y 3 no parten de cero: se apoyan en cómo se estructuran habitualmente los proyectos FastAPI. Esta sección explica qué tomamos de esas convenciones, qué adaptamos a Brasaland y por qué, sin repetir el detalle que ya está en las secciones anteriores.

Fuentes consultadas: la documentación oficial de FastAPI, la plantilla oficial *Full Stack FastAPI Template* y la guía comunitaria *FastAPI Best Practices*. Los enlaces están en la sección 8.

### 4.1 Estructura de carpetas

| Convención | Qué adoptamos | Qué cambiamos y por qué |
|---|---|---|
| **Documentación oficial ("Bigger Applications"):** un `main.py` pequeño que registra routers, con las rutas agrupadas en una carpeta `routers/` y las dependencias compartidas en un archivo común. | `main.py` solo registra routers y no contiene rutas de negocio (3.1). | No agrupamos por tipo de archivo. La guía oficial muestra una aplicación con dos o tres áreas; con 14 dominios, una carpeta `routers/` y otra `models/` con decenas de archivos mezclarían áreas del negocio sin relación entre sí (2.1). |
| **Guía comunitaria:** un paquete por dominio con sus propios archivos de rutas, esquemas, modelos, servicio, dependencias y excepciones, más el código transversal en la raíz (configuración, base de datos, paginación, errores). | La plantilla interna de cada dominio (2.4) y la carpeta `core/` (2.6) siguen esta convención casi sin cambios. | Añadimos un archivo `repository.py`, que separa las consultas a la base de datos de las reglas de negocio, como exige la capa de datos de la sección 1. Añadimos también `integrations/` y `jobs/`, que la guía no contempla: Brasaland tiene POS por país, tareas programadas y proveedores externos que no encajan en ningún dominio. |
| **Plantilla oficial *Full Stack*:** backend y frontend en carpetas separadas, cada uno con su README, sus dependencias y su configuración de Docker. | El backend vive en `services/brasaland-api/`, separado de los frontends de `uis/` (2.2), con `pyproject.toml`, `Dockerfile`, `.env.example` y `README.md` propios (2.3). | En la plantilla, la API sirve el frontend desde el mismo dominio. En Brasaland, frontends y API son sistemas separados en orígenes distintos, así que el navegador exigirá que la API autorice explícitamente esos orígenes (CORS, ver 5.4). |

### 4.2 Routers

La documentación oficial propone dividir la aplicación en routers, cada uno con un **prefijo**, unas **etiquetas** y unas **dependencias comunes**, y registrarlos todos desde `main.py`. De ahí salen tres decisiones de la sección 3:

- **Un router por dominio,** registrado bajo `/api/v1`. FastAPI permite añadir el prefijo de versión al registrar el router, sin repetirlo en cada ruta.
- **Requisitos comunes declarados en el router.** La autenticación y los roles se definen una vez por dominio. FastAPI ejecuta las dependencias del router antes que las de cada ruta, lo que garantiza que ninguna ruta del dominio quede desprotegida por olvido.
- **Etiquetas por dominio.** Según la documentación oficial, las etiquetas no solo agrupan la documentación: los generadores de clientes TypeScript crean un servicio por etiqueta. Ese es el motivo para elegir la etiqueta por dominio y no por recurso.

### 4.3 Modelos y esquemas

La documentación oficial recomienda **no usar un único modelo** para la tabla, la entrada y la salida. Propone varios modelos derivados de una base común:

- uno para la tabla,
- uno para lo que se devuelve al cliente,
- uno para crear,
- uno para modificar, con todos los campos opcionales.

Su argumento es concreto: con un único modelo, el cliente podría fijar campos que le corresponden al servidor (el identificador) y la API expondría campos internos.

Esta recomendación es la base de dos decisiones ya documentadas:

- **La separación entre `schemas.py` y `models.py` en cada dominio (2.4).** Es especialmente relevante en `people/`, `customers/` y `auth/`, que guardan datos personales o credenciales que no deben aparecer en todas las respuestas.
- **El uso de `PATCH` con campos opcionales para modificar (3.2).** Solo se actualiza lo que el cliente envía.

La librería concreta para definir tablas y esquemas está pendiente (sección 7). El patrón de modelos separados se aplica con cualquiera de las opciones.

### 4.4 Configuración

La documentación oficial recomienda definir la configuración como una **clase tipada que lee variables de entorno**. Se valida al arrancar y se entrega a las rutas como una dependencia, lo que permite sustituirla en las pruebas. Adoptamos ese enfoque con estas reglas:

- **Toda la configuración entra por variables de entorno:** cadena de conexión a la base de datos, orígenes permitidos para los frontends, credenciales de POS, del proveedor de IA y del correo, y entorno (desarrollo, pruebas o producción).
- **El servicio no arranca si falta una variable obligatoria o tiene un formato inválido.** Es preferible fallar al desplegar que descubrir el error en mitad de un cierre de caja.
- **El repositorio contiene `.env.example`**, con los nombres de las variables y sin valores reales. El `.env` con valores reales nunca se sube al repositorio.
- **Una configuración general en `core/config.py`.** Solo las integraciones que tengan credenciales propias (cada POS, el proveedor de IA, el correo) definen su propia sección de configuración, junto a su adaptador. La guía comunitaria sugiere dividir la configuración por módulo. La adoptamos solo para las integraciones, porque son las únicas partes con credenciales y valores propios. Para los dominios sería fragmentar sin necesidad.
- **La documentación interactiva de la API depende del entorno.** Visible en desarrollo y pruebas, oculta o protegida en producción (3.4).

La investigación también cubrió temas que no afectan a la estructura, como la base de datos, la autenticación o las tareas en segundo plano. Se recogen como decisiones pendientes en la sección 7.

---

## 5. Frontend y backend como sistemas separados

Brasaland tendrá varios clientes de una misma API:

- el talent-pipeline-tracker,
- el futuro backoffice,
- la web corporativa,
- la app de fidelización,
- la plataforma de formación,
- los agentes de IA.

Esta sección define cómo se relacionan con el backend. Algunas piezas ya aparecen en secciones anteriores; aquí se reúnen y se completan.

### 5.1 Un solo repositorio, sistemas independientes

**Decisión: mantener el monorepo actual.** Frontends y backend viven en el mismo repositorio, pero se construyen, se configuran y se despliegan por separado.

"Separados" se refiere a los **sistemas**, no a los repositorios. Es fácil confundirlo. Lo que hace independientes al frontend y al backend no es dónde está guardado el código, sino tres reglas:

1. **No comparten código.** El backend no importa nada de `uis/`, y los frontends no importan nada de `services/`.
2. **Se comunican solo por HTTP**, a través del contrato de la API (5.2).
3. **Cada uno tiene su propia configuración, dependencias y despliegue.**

Por qué el monorepo encaja con Brasaland:

- **Un cambio de contrato y su adaptación en el frontend pueden ir juntos.** La transición del tracker a `/candidates` (3.5) se revisa y se integra en un solo cambio, en lugar de coordinar dos repositorios.
- **Un equipo pequeño mantiene un solo lugar** para el contexto del negocio, la documentación y las reglas de trabajo, que hoy viven en la raíz del repositorio.
- **Ya es la estructura del proyecto,** y el repositorio separa por carpetas los frontends (`uis/`), los servicios (`services/`) y los agentes (`agents/`).

Por qué no repositorios separados:

- Aportan permisos y ciclos de publicación independientes por equipo, algo que Brasaland no necesita con un único equipo de tecnología.
- Su coste sería sincronizar versiones del contrato entre repositorios en cada cambio.

**Lo que hay que cuidar:**

- El repositorio mezcla dos ecosistemas (Node.js y Python) y no tiene herramientas comunes en la raíz. Las comprobaciones automáticas (pruebas, linter, construcción) deben ejecutarse **solo en el proyecto que cambió**, para que tocar el tracker no obligue a probar el backend y viceversa.
- La regla 1 no la impone ninguna herramienta. Se vigila en las revisiones de código.

### 5.2 Comunicación a través del contrato de la API

- **La única fuente de verdad es el contrato que publica el backend** (`/openapi.json`, sección 3.4). FastAPI lo genera automáticamente a partir de las rutas y los esquemas; nadie lo escribe a mano.
- **Cada frontend genera su cliente TypeScript a partir de ese contrato** y lo guarda en su propia carpeta. Hoy el tracker define sus tipos a mano y los ha tenido que deducir probando la API (3.5). Con un cliente generado, si el backend cambia un campo, el frontend deja de compilar en lugar de fallar en producción.
- **Flujo de un cambio en la API:**
  1. Se modifica el backend.
  2. Se regenera el cliente en los frontends afectados.
  3. Se corrigen los errores de tipo que aparezcan.
  4. Todo se integra en el mismo cambio, gracias al monorepo.
- **Los agentes de IA son clientes como cualquier otro.** Llaman a la API por HTTP con sus propias credenciales y permisos; nunca acceden directamente a la base de datos (2.2).
- **Las llamadas salen directamente desde el navegador hacia la API,** como ya hace el tracker. Next.js permite además usar el servidor del frontend como intermediario (patrón *Backend for Frontend*). No lo adoptamos de entrada porque añade una capa más sin un problema concreto que resolver. Se reconsiderará si la estrategia de autenticación lo requiere, por ejemplo para guardar la sesión en una cookie inaccesible desde JavaScript. Esa estrategia está pendiente (sección 7).
- **La autorización vive siempre en el backend.** Que un frontend oculte un botón no protege nada: cada ruta de la API comprueba los permisos por sí misma (3.1, 3.2), sea quien sea el cliente.

### 5.3 Variables de entorno en cada lado

La configuración del backend se describe en 4.4. En los frontends hay una diferencia importante con Next.js:

- **Las variables con prefijo `NEXT_PUBLIC_` se incrustan en el código que se descarga en el navegador** al construir la aplicación. Cualquier usuario puede leerlas.
- **Regla:** en un frontend, solo son variables públicas las que sería aceptable publicar en una página web, como la URL base de la API (`NEXT_PUBLIC_API_BASE_URL`, que el tracker ya usa). Claves, tokens y credenciales de proveedores nunca van en un frontend; pertenecen al backend.
- **Consecuencia:** como el valor queda fijado al construir, cada entorno (desarrollo, pruebas, producción) necesita su propia construcción del frontend apuntando a su API.

**Cada proyecto tiene su propio archivo de entorno y su propio `.env.example`.** No hay un `.env` compartido en la raíz: mezclaría la configuración de sistemas que se despliegan por separado y facilitaría exponer en un frontend un secreto del backend.

**Hay un punto de coordinación obligatorio entre ambos lados:** la URL de la API que conoce cada frontend y la lista de orígenes que autoriza el backend (5.4) deben coincidir en cada entorno. Si no coinciden, el navegador bloquea las peticiones aunque los dos sistemas funcionen correctamente por separado.

### 5.4 CORS

Un navegador solo permite que una página llame a una API de otro origen si esa API lo autoriza expresamente. El origen es la combinación de protocolo, dominio y puerto.

En Brasaland, los frontends y la API son siempre orígenes distintos:

- en desarrollo, porque se ejecutan en puertos distintos;
- en producción, porque se publican en dominios distintos.

Por tanto, CORS es necesario desde el primer endpoint. Política propuesta:

- **Lista explícita de orígenes permitidos**, distinta por entorno y leída de una variable de entorno del backend. Incluye solo los frontends que llaman a la API desde el navegador.
- **Nunca el comodín `*`.** Además de abrir la API a cualquier web, deja de funcionar en cuanto las peticiones llevan credenciales, como la cabecera de autenticación que usarán todas las rutas protegidas.
- **Solo los métodos y cabeceras que la API usa:** `GET`, `POST`, `PATCH` y `DELETE`; las cabeceras de autenticación y de tipo de contenido.
- **Si el frontend añade un intermediario en el servidor (5.2),** sus llamadas dejan de venir del navegador y ese frontend ya no necesitaría estar en la lista.

Dos aclaraciones para el equipo, porque son fuente habitual de confusión:

- **CORS no es un mecanismo de seguridad de la API.** Solo lo aplican los navegadores. Un script, un agente de IA, un POS o una app móvil nativa pueden llamar a la API sin pasar por CORS. Lo que protege la API es la autenticación y la autorización.
- **Un error de CORS casi nunca es un error del frontend.** Normalmente significa que el origen no está en la lista del backend para ese entorno (5.3).

### 5.5 Despliegue independiente

Frontend y backend se despliegan por separado, así que durante un tiempo convivirán una versión nueva de uno con la anterior del otro. Para que eso no rompa nada:

- **Los cambios de la API se despliegan primero y son compatibles con lo anterior.** Por ejemplo, un campo nuevo se añade sin retirar el antiguo. Después se despliegan los frontends que lo usan, y solo entonces se retira lo obsoleto.
- **Un cambio que no se pueda hacer de forma compatible requiere una nueva versión de la API** (`/api/v2`, sección 3.1). Mientras tanto, la versión anterior sigue disponible hasta que todos los clientes hayan migrado.

La transición del tracker (3.5) es la excepción. Como hoy consume otra API y no la nuestra, se cambia de una vez en el sprint en que se implementa `recruitment/`.

---

## 6. Riesgos y puntos de atención

La estructura propuesta solo funciona si se aplica con constancia: FastAPI no impide saltarse ninguna de sus reglas (1.5). Esta sección recoge qué podría salir mal, empezando por lo que ocurriría si el equipo no la sigue.

### 6.1 Qué puede salir mal si no se sigue la estructura

#### Reglas de negocio escritas en los endpoints

- **Qué pasaría.** Cada endpoint resuelve a su manera la conversión COP/USD, la hora local o el cálculo del ticket promedio. El dashboard ejecutivo, el informe del lunes y el ranking de locales acaban mostrando **cifras distintas para la misma pregunta**, por ejemplo "cuánto vendimos esta semana en Florida". La dirección deja de confiar en los datos, que es justo el problema que este proyecto debe resolver.
- **Señal de alerta.** Un `router.py` que hace cálculos, importa la base de datos o contiene condiciones del tipo "si el país es Colombia…".
- **Cómo evitarlo.** Las reglas 1 y 2 de la sección 1.4. Dinero y zonas horarias solo a través de `core/` (2.6), y métricas compartidas solo en `reporting` (2.5).

#### Un dominio que escribe en las tablas de otro

- **Qué pasaría.** Por comodidad, `inventory` descuenta stock consultando directamente la tabla de ventas, y `loyalty` suma puntos escribiendo junto a cada venta. Cuando `sales` cambie su esquema (por ejemplo, para admitir el formato del POS de Florida), **inventario y fidelización fallarán sin que nadie lo haya previsto**. Además, el monolito dejaría de poder dividirse: ningún módulo podría extraerse sin arrastrar a los demás (1.5).
- **Señal de alerta.** Un dominio que importa `models.py` o `repository.py` de otro dominio.
- **Cómo evitarlo.** Las reglas de 2.5: cada tabla tiene un único dueño y un dominio solo usa otro a través de su `service.py`.

#### Integraciones externas usadas sin su adaptador

- **Qué pasaría.** `sales` llama directamente a la librería del POS colombiano. Cuando se integre el de Florida, o cuando cualquiera de los dos cambie de proveedor, **habrá que reescribir las reglas de ventas** en lugar de añadir un adaptador. Además, las pruebas de ventas pasarían a depender de un POS real. Lo mismo ocurre con la tasa de cambio, que hoy es fija y algún día será variable.
- **Señal de alerta.** Una librería de un proveedor importada fuera de `integrations/`.
- **Cómo evitarlo.** La regla 5 de la sección 1.4.

#### Tipos del frontend escritos a mano o sin regenerar

- **Qué pasaría.** Se repiten los problemas que hoy tiene el tracker (3.5): valores deducidos a ojo, envoltorios de respuesta inesperados y llamadas extra para corregir lo que la API ignora. Un cambio del backend **rompe el frontend en producción en lugar de en la compilación**.
- **Cómo evitarlo.** Clientes generados desde el contrato y regenerados en el mismo cambio que modifica la API (5.2).

#### "Arreglar" un error de configuración abriendo la puerta

- **Qué pasaría.** Ante un error de CORS, alguien configura el comodín `*` para "que funcione". O, para no pasar por el backend, coloca una clave de un proveedor en una variable `NEXT_PUBLIC_`. En el primer caso la API acepta peticiones de cualquier web. En el segundo, **la clave queda publicada en el navegador** de cualquier usuario.
- **Cómo evitarlo.** Las políticas de 5.3 y 5.4. Un error de CORS se resuelve añadiendo el origen correcto a la lista del entorno.

#### Procesos pesados dentro de la API

- **Qué pasaría.** El informe semanal o la comprobación de locales sin ventas se ejecutan en el mismo proceso que atiende a los usuarios. **Cada lunes a las 7:00 el backoffice va lento** justo cuando la dirección consulta los datos de la semana.
- **Cómo evitarlo.** Este trabajo va en `jobs/`, en un proceso aparte (2.6).

#### Fechas guardadas en hora local

- **Qué pasaría.** "Ventas de hoy" se calcula mal en los locales de Florida durante el horario de verano. La alerta de "local sin ventas en horario de apertura" **salta cuando el local aún está cerrado**, o no salta cuando debería. Una alerta que falla unas cuantas veces deja de tomarse en serio.
- **Cómo evitarlo.** Fechas en UTC y conversión con la zona horaria de cada local, siempre a través de `core/timezones.py` (3.2).

### 6.2 Riesgos del proyecto

| Riesgo | Por qué importa | Respuesta propuesta |
|---|---|---|
| **Reglas de negocio duplicadas en TypeScript y en Python.** `src/` ya implementa validaciones y cálculos (margen, ticket promedio, métricas por país). | Si el backend las reimplementa y alguien sigue usando las de `src/`, habrá dos versiones de la misma regla que divergen con el tiempo. | El backend pasa a ser la fuente de verdad de las reglas de negocio. `src/` queda como referencia para portar la lógica y no se amplía con reglas nuevas. |
| **No sabemos cómo funcionan los POS.** Solo sabemos que hay uno distinto en cada país y que no están integrados. | Determina si las ventas llegan por carga periódica, por avisos automáticos (webhooks) o por exportación de archivos. Eso afecta a `sales` y a la puntualidad de las alertas. | Averiguarlo antes de empezar `sales/`. La interfaz común (`integrations/pos/`) permite avanzar con un adaptador de prueba mientras tanto. |
| **Base de datos, autenticación e infraestructura sin decidir.** | La estructura no depende de ellas, pero el primer endpoint real sí. | Cerrar las decisiones de la sección 7 antes del primer sprint de desarrollo. |
| **Construir los 14 dominios antes de tiempo.** | El árbol de 2.3 es un mapa de destino. Crear carpetas vacías o modelos especulativos para todos los dominios ralentiza al equipo y fija fronteras antes de conocer bien el negocio. | Crear cada dominio cuando se empiece a trabajar en él (2.7). |
| **La excepción de `reporting` se convierte en una puerta trasera.** | Si `reporting` empieza a escribir datos, o si otros dominios copian su forma de leer tablas ajenas, la regla de 2.5 deja de existir en la práctica. | `reporting` solo hace consultas de solo lectura, y la excepción no se extiende a ningún otro dominio sin una decisión explícita. |
| **Brasa Points depende de las ventas.** | Si `sales` llama directamente a `loyalty` al registrar cada venta, aparece una dependencia entre dominios operativos que no está en 2.5, y un fallo en fidelización podría bloquear el registro de ventas. | La acumulación de puntos la procesa un job a partir de las ventas nuevas, sin que `sales` conozca a `loyalty`. |
| **Pedidos en línea fuera del mapa.** `CONTEXT.md` menciona una app de fidelización **y de pedidos**. | La propuesta no incluye un dominio de pedidos digitales. Si entra en el alcance, generará ventas que hoy solo llegan desde los POS. | Tratarlo como un dominio nuevo (`orders/`) cuando se priorice, sin mezclarlo con `sales`. |
| **Un monorepo sin herramientas comunes.** | Sin comprobaciones separadas por proyecto, cada cambio obliga a probarlo todo o, peor, a no probar nada. | Comprobaciones automáticas por carpeta (5.1). |

### 6.3 Términos que pueden causar confusión

Varias palabras significan cosas distintas según quién las use. Conviene fijarlas desde el principio para no acabar con endpoints duplicados:

| Término | Significados posibles | Dónde va cada uno |
|---|---|---|
| **Onboarding** | Alta administrativa (contrato, documentación, legislación del país) frente a itinerario de formación (horas por estación, tareas progresivas). | `people/` y `training/` respectivamente. |
| **Usuario / empleado** | Una cuenta para acceder a la plataforma frente a una persona contratada por Brasaland. No todo empleado tendrá cuenta, y puede haber cuentas que no sean de empleados. | `auth/` y `people/`. |
| **Producto / receta** | Lo que se vende, con su precio por país, frente a cómo se prepara, con ingredientes, pasos y versiones. | `menu/` y `recipes/`. |
| **Ventas / telemetría** | Transacciones con dinero, normalizadas desde los POS, frente a eventos operativos en tiempo real (local abierto, terminal conectado…). | `sales/` y `telemetry/`. |
| **Records / candidatos** | El nombre del recurso en la API que consume hoy el tracker frente al vocabulario del dominio. | `/candidates` (3.5). |
| **Sistemas separados / repositorios separados** | Frontend y backend independientes frente a código en repositorios distintos. | Sistemas separados en un mismo repositorio (5.1). |

### 6.4 Cómo se mantiene la estructura en el tiempo

- **Revisión de código con una lista corta de comprobaciones,** derivada de 6.1:
  - ¿Hay reglas de negocio en un router?
  - ¿Algún dominio importa modelos o repositorios de otro?
  - ¿Hay librerías de proveedores fuera de `integrations/`?
  - ¿Se regeneró el cliente del frontend?
  - ¿Hay secretos en variables públicas?
- **Comprobación automática de imports entre capas y dominios,** cuando el número de dominios lo justifique. Detecta en la integración continua lo que una revisión puede pasar por alto.
- **La plantilla de dominio (2.4) como punto de partida obligatorio** para cada módulo nuevo.
- **Las reglas, también para los asistentes de IA.** Este repositorio ya define instrucciones para agentes de IA (`AGENTS.md` y `.agents/rules/`). Si las reglas de esta propuesta no se trasladan ahí, el código generado con asistencia de IA puede ignorarlas tanto como un miembro nuevo del equipo.

---

## 7. Decisiones técnicas pendientes

Esta propuesta define la estructura del backend, pero deja abiertas varias decisiones técnicas que no la condicionan. Todas deben cerrarse antes del primer sprint de desarrollo (6.2):

| Decisión | Qué condiciona | Dónde se menciona |
|---|---|---|
| **Motor de base de datos, librería para tablas y esquemas, y herramienta de migraciones** | `core/database.py`, los `models.py` de cada dominio y `migrations/`. | 2.3, 4.3 |
| **Estrategia de autenticación** (incluido si los clientes de la app de fidelización comparten el acceso de los usuarios internos) | `auth/` y `core/security.py`. Si la sesión se guarda en una cookie, condiciona también el uso de un intermediario en Next.js y la configuración de CORS con credenciales. | 3.3, 5.2, 5.4 |
| **Tecnología para el flujo en tiempo real** | `GET /telemetry/stream` y el dashboard operativo. | 3.3 |
| **Ejecución de tareas programadas y de fondo** | Cómo se lanzan y se reintentan los procesos de `jobs/`. | 2.6 |
| **Criterio para usar funciones asíncronas** | Rendimiento de las rutas y de los adaptadores de POS e IA, cuyas llamadas externas no deben bloquear la API. | 4 |
| **Herramientas de pruebas y de formato de código** | La estructura de `tests/` y las comprobaciones automáticas por proyecto. | 2.3, 5.1 |
| **Infraestructura y hosting** | Los orígenes de CORS por entorno, el despliegue independiente y las comprobaciones automáticas. | 5.3, 5.4, 5.5 |

---

## 8. Fuentes

- FastAPI — Bigger Applications: https://fastapi.tiangolo.com/tutorial/bigger-applications/
- FastAPI — SQL Databases (modelos múltiples): https://fastapi.tiangolo.com/tutorial/sql-databases/
- FastAPI — Settings and Environment Variables: https://fastapi.tiangolo.com/advanced/settings/
- FastAPI — Generating Clients: https://fastapi.tiangolo.com/advanced/generate-clients/
- FastAPI — CORS: https://fastapi.tiangolo.com/tutorial/cors/
- Full Stack FastAPI Template: https://github.com/fastapi/full-stack-fastapi-template
- FastAPI Best Practices (zhanymkanov): https://github.com/zhanymkanov/fastapi-best-practices
- Next.js — Backend for Frontend: https://nextjs.org/docs/app/guides/backend-for-frontend
