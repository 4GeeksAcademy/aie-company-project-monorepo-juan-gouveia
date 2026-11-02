# Project Brief

## Descripción del Negocio

**Brasaland** es una cadena de restaurantes de comida a la parrilla fundada en 2008 en Medellín, Colombia. Lo que comenzó como un único local familiar se ha convertido, en más de quince años, en una cadena de **14 restaurantes propios** que operan en **dos países**: Colombia y Estados Unidos (Florida). La empresa emplea aproximadamente a **115 personas** y genera alrededor de **6 millones de dólares en ingresos anuales**.

La marca se sostiene sobre tres pilares fundamentales:
1. **Consistencia del producto** — la comida sabe igual se pida en Medellín o en Miami.
2. **Experiencia de servicio cálida y uniforme** en todos los locales.
3. **Operación de cocina eficiente** que mantiene el ritmo en horas pico.

La compañía está liderada por **Mariana Restrepo** (CEO, hija del fundador), quien desde 2019 impulsa la expansión al mercado estadounidense y la modernización de los sistemas internos. La organización se divide en siete áreas: Operaciones de Restaurante, Compras y Proveedores, Marketing y Experiencia Digital, Personas y Cultura, Formación y Estándares de Calidad, Tecnología, y Dirección Ejecutiva.

Brasaland es rentable y tiene una base de clientes leales en ambos mercados, pero enfrenta el desafío de gestionar una operación bicountry con herramientas diseñadas para un restaurante local.

---

## Problema que Resuelve

Brasaland opera 14 restaurantes en dos países sin un ecosistema digital integrado. Las consecuencias de esta carencia se manifiestan en todos los departamentos:

### 🍖 Operaciones de Restaurante
- No existe visibilidad centralizada de ventas en tiempo real por local.
- Los pedidos de ingredientes se hacen por WhatsApp o teléfono, sin datos de inventario, generando sobrestock en unos locales y desabastecimiento en otros.
- Los reportes de turno se llenan en papel o Excel y se envían semanalmente a RRHH.

### 🛒 Compras y Proveedores
- Negociación de precios por correo y Excel con ~20 proveedores.
- No hay datos consolidados de gasto en toda la cadena.
- Los cambios de precio se descubren cuando llega la factura.

### 📱 Marketing y Experiencia Digital
- Sitio web desactualizado (2019) sin pedidos en línea.
- App con calificación de 2.8 estrellas en las tiendas.
- Programa de fidelización ("Brasa Points") con tarjetas físicas que el 60% de los clientes no usa y que no genera datos.
- No hay información sobre quiénes son los clientes.

### 🧑‍🤝‍🧑 Personas y Cultura
- Procesos de RRHH gestionados por email y Excel.
- Onboarding de personal de cocina (alta rotación) completamente manual.
- Complejidad adicional por dos legislaciones laborales distintas.

### 🎓 Formación y Estándares de Calidad
- Materiales de formación en Google Drive sin navegación clara.
- Las actualizaciones de recetas tardan días en comunicarse a 14 locales.
- Sin sistema estructurado de incorporación para nuevo personal.

### 💻 Tecnología
- Stack tecnológico mínimo: web estática, app desactualizada, POS distintos en cada país sin integración.
- No hay API interna, datos consolidados ni telemetría.

### 📊 Dirección Ejecutiva
- Decisiones basadas en llamadas telefónicas, reportes PDF semanales e intuición.
- Imposibilidad de responder en tiempo real a preguntas básicas como "¿cuánto vendimos esta semana en Florida?".

Este proyecto aborda estos problemas construyendo la plataforma digital de Brasaland desde una base cercana a cero, automatizando procesos, centralizando datos y habilitando capacidades de IA para la toma de decisiones.

---

## Objetivos del Proyecto

### Objetivo General

Construir las herramientas, sistemas y automatizaciones que permitan a Brasaland operar como una empresa moderna, integrando sus 14 locales en dos países bajo una plataforma digital unificada que preserve la calidad y consistencia que definen su marca.

### Objetivos Específicos

#### 1. Centralización de Datos y API Unificada
- Desarrollar una API central de Brasaland que cubra locales, menús, ventas, clientes y proveedores.
- Implementar un pipeline de datos que alimente dashboards de operaciones, marketing y finanzas.

#### 2. Visibilidad Operativa en Tiempo Real
- Crear un dashboard de ventas en tiempo real por local (en COP y USD).
- Sistema de alertas automáticas cuando un local no registre ventas en horario de apertura.
- Telemetría en tiempo real desde cada local.

#### 3. Gestión Inteligente de Inventarios y Compras
- Sistema de pedidos de ingredientes basado en ventas históricas y stock actual.
- Plataforma de gestión de proveedores con historial de precios y alertas.
- Visibilidad consolidada de compras para negociación centralizada.

#### 4. Experiencia Digital para el Cliente
- Aplicación de fidelización y pedidos digitales.
- CRM de clientes con historial de pedidos y preferencias.
- Motor de personalización que sugiera productos relevantes según comportamiento.

#### 5. Automatización de RRHH y Formación
- Portal interno de RRHH para solicitudes de vacaciones y gestión de ausencias.
- Flujo automatizado de onboarding para nuevo personal.
- Dashboard de KPIs de RRHH (rotación, absentismo, tiempo de cobertura) segmentado por país.

#### 6. Plataforma de Formación y Estándares de Calidad
- Recetario interactivo y buscable.
- Itinerario estructurado de incorporación para nuevo personal.
- Sistema de publicación de actualizaciones de recetas simultáneo a todos los locales.
- Soporte multilingüe (español/inglés).

#### 7. Asistencia IA para la Dirección
- Asistente de IA consultable en lenguaje natural.
- Dashboard ejecutivo con ventas totales de la cadena en USD y COP.
- Informe semanal automatizado generado y enviado cada lunes a las 7:00 AM.

---

## Alcance del Proyecto

El proyecto se desarrolla en el marco del programa AI Engineering de 4Geeks Academy, siguiendo la estructura de monorepo por capas del template oficial. Cada hito del programa (Web, Programación, Backend, Telemetría, RAG, Agentes, Workflows, Tiempo Real) se corresponde con entregables específicos dentro de este repositorio.

La empresa seleccionada es **Brasaland**, y el enfoque personal del proyecto se centra en tres áreas prioritarias definidas en la elección del estudiante:
1. **Operaciones de Restaurante** — control de stock automatizado y escalable.
2. **Marketing y Experiencia Digital** — sistema de fidelización robusto.
3. **Formación y Estándares de Calidad** — plataforma de formación con recetario interactivo e itinerario de incorporación.

---

_Actualizado: 2026-10-09_