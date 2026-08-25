# Auditoría de alimentación de la Base Maestra a toda la plataforma

Fecha: 2026-08-24  
Alcance: auditoría estructural del código, contratos SQL, publicación, consumidores y pruebas automatizadas.  
Naturaleza: diagnóstico; este informe no modifica datos ni activa sincronizaciones.

## Dictamen ejecutivo

La Base Maestra **sí consolida y publica** cuatro conjuntos canónicos (`master_ninos`, `master_salud_nutricion`, `master_talento_humano` y `master_unidades`), pero **no existe un mecanismo único que obligue a todos los módulos a consumirlos ni una propagación automática después de publicar**.

La plataforma mantiene una arquitectura híbrida:

1. Algunos módulos consultan directamente las tablas `master_*` y reciben la versión publicada.
2. Otros consultan copias históricas (`beneficiarios`, `usuarios`, `coordinadores`, `th_personas`, `th_asignaciones`, `gp_*`, `unidades`).
3. Algunos usan la Base Maestra solo como respaldo si la tabla antigua no existe. Como las tablas antiguas normalmente existen, el respaldo nunca se ejecuta, aunque estén vacías o desactualizadas.
4. La publicación solo cambia indicadores `activo` y la versión vigente. No ejecuta sincronización de Talento Humano, Gestión Pedagógica, Gestión por Coordinador, Planeación ni demás proyecciones.

Por eso la regla funcional “cargar una vez y alimentar toda la plataforma” todavía no está garantizada por arquitectura.

## Hallazgos críticos

### H1. Publicar no propaga a los consumidores operativos — CRÍTICO

`publicar_version()` archiva la versión anterior, activa la nueva y actualiza `activo` en las cuatro tablas maestras. Después registra la publicación y termina. No existe un despachador de eventos, cola de sincronización, tabla de proyecciones pendientes ni llamadas a los servicios consumidores.

Consecuencia: los módulos conectados directamente cambian; las copias `th_*`, `gp_*`, `beneficiarios`, `usuarios` y `unidades` conservan el estado anterior.

### H2. Talento Humano tiene dos fuentes maestras incompatibles — CRÍTICO

La Base Maestra publica personal en `master_talento_humano`, pero `TalentoHumanoService.sincronizar_global()` obtiene sus filas mediante `list_talento()`, y esa función lee la tabla histórica `coordinadores`. Luego materializa `th_personas`, `th_asignaciones`, `gp_coordinadores`, `gp_docentes`, `gp_equipos_interdisciplinarios` y asignaciones.

Consecuencia: subir Talento Humano dentro de Base Maestra no activa ese circuito. Coordinadores, docentes y equipos pueden aparecer en el panel maestro pero faltar en los módulos operativos.

### H3. La relación niño–docente/coordinador no se enriquece desde Talento Humano — CRÍTICO

Durante la consolidación se agrupa talento por unidad para contar `total_talento`, pero los campos `docente` y `coordinador` de `master_ninos` se insertan desde el registro de Cuéntame. No se completan con el docente/coordinador identificado en `master_talento_humano`.

Consecuencia: cuando Cuéntame no trae esos campos, los niños quedan “sin docente” aunque Talento Humano sí tenga la asignación por unidad.

### H4. `master_unidades` se construye solo desde niños — ALTO

El catálogo recorre las unidades presentes en `ninos`. Talento Humano solo aporta el conteo para una unidad ya creada. Una unidad presente únicamente en Talento Humano no entra a `master_unidades`; además, su coordinador se toma inicialmente de Cuéntame.

Consecuencia: catálogos incompletos y coordinadores ausentes o divergentes.

### H5. Hay consumidores que prefieren la copia antigua — ALTO

Centro de Planeación/RAM consulta `beneficiarios` si la tabla tiene columnas y solo usa `master_ninos` cuando la tabla histórica no existe. La existencia del esquema es suficiente para bloquear el origen canónico.

Consecuencia: una tabla histórica vacía o atrasada gana sobre la Base Maestra publicada.

### H6. No hay un contrato común de lectura — ALTO

Cada módulo escribe SQL propio y aplica de forma diferente `fundacion_id`, `activo`, `version_id`, estado de retiro, nombres de unidad y documento. No hay repositorio/servicio obligatorio para participantes, personal, unidades y salud.

Consecuencia: resultados distintos para el mismo dato, riesgo de mezcla entre versiones y más correcciones aisladas.

### H7. Las pruebas verifican módulos, no la propagación total — ALTO

Las pruebas revisadas pasan para Base Maestra, mapeo de talento, Centro de Planeación, Salud Integral y Gerencia. Sin embargo, no existe una prueba extremo a extremo que publique una versión y confirme el mismo participante, docente, coordinador, unidad y dato nutricional en todos los módulos consumidores.

Consecuencia: el sistema puede aprobar pruebas locales mientras falla la regla global.

## Matriz de consumidores

| Estado | Módulos / funciones | Fuente observada | Riesgo |
|---|---|---|---|
| Directo | Relación del mes, Paquete mensual, Reportes gerenciales, Gerencia general, búsqueda/diagnóstico principal | `master_ninos`, `master_talento_humano`, `master_salud_nutricion`, `master_unidades` | Menor, siempre que filtren `activo` y `fundacion_id` |
| Directo o mayormente directo | Centro Documental, Familias y Redes, Salud Integral, Gestión Integral UCA, Calidad de Datos, Cruce de Bases | tablas `master_*` | Medio: algunas funciones admiten orígenes heredados |
| Parcial / respaldo | Centro de Planeación y RAM, Componente Psicosocial | `beneficiarios`/`usuarios` primero o múltiples orígenes; `master_ninos` como alternativa | Alto: puede mostrar copias antiguas |
| Proyección separada | Talento Humano integral | `coordinadores` → `th_personas`/`th_asignaciones` | Crítico: no parte de `master_talento_humano` |
| Proyección separada | Gestión Pedagógica y Gestión por Coordinador | `gp_coordinadores`, `gp_docentes`, `gp_equipos_interdisciplinarios`, `gp_unidades_asignadas` | Crítico: requiere sincronización ajena a publicación |
| Operativo independiente | Planeación Pedagógica, Calendario, Motor de Gestión, Supervisión, Ambientes Protectores | tablas transaccionales propias | Correcto para actividades/evidencias, pero sus selectores de población, UDS y responsables deben venir del contrato maestro |
| Sin relación poblacional esperada | Seguridad, facturación, temas, backups, panel comercial | tablas propias | No deben copiar participantes; solo requieren identidad/tenant cuando corresponda |

## Causa raíz

La causa no es un único error de mapeo. Es una **duplicación de fuentes de verdad** acumulada durante la evolución de la plataforma. Base Maestra fue añadida como fuente canónica, pero los módulos anteriores conservaron repositorios y tablas propias. No se completó la migración con:

- un contrato canónico obligatorio;
- proyecciones automáticas e idempotentes;
- evento posterior a publicación;
- control de versión consumida por módulo;
- pruebas de consistencia entre módulos.

## Arquitectura requerida para cumplir la regla global

### Fuente única

Crear una capa obligatoria `MasterDataProvider` con cuatro interfaces de solo lectura:

- participantes activos y retirados;
- talento humano y asignaciones;
- unidades y responsables;
- salud y nutrición.

Ningún módulo debe consultar directamente `beneficiarios`, `usuarios`, `coordinadores`, `th_personas` o `gp_*` para resolver identidad maestra.

### Separación correcta

La Base Maestra debe alimentar datos de referencia. Los módulos conservan únicamente sus transacciones:

- una planeación pertenece a Planeación;
- un seguimiento pertenece a Psicosocial;
- una valoración profesional pertenece a Salud;
- una evidencia pertenece a su módulo;
- pero participante, documento, unidad, docente, coordinador y cargo se resuelven desde Base Maestra.

### Publicación atómica

Después de publicar una versión se debe:

1. activar la versión maestra;
2. enriquecer niño–unidad–docente–coordinador desde Talento Humano;
3. construir unidades desde la unión de Cuéntame y Talento Humano;
4. reconstruir proyecciones heredadas necesarias, de forma idempotente;
5. registrar por módulo la versión consumida y los totales;
6. fallar o marcar publicación parcial si algún consumidor obligatorio no se actualiza.

### Compatibilidad temporal

Mientras existan tablas antiguas, deben convertirse en vistas/proyecciones derivadas o actualizarse automáticamente. Nunca deben competir con `master_*` ni ganar solo por existir.

## Plan de corrección priorizado

### QAP 1 — consistencia central

1. Implementar `MasterDataProvider` con filtro obligatorio por `fundacion_id`, versión activa y estado.
2. Enriquecer `master_ninos.docente` y `.coordinador` usando asignaciones únicas de `master_talento_humano` por unidad.
3. Construir `master_unidades` desde la unión de unidades de niños y talento.
4. Cambiar Talento Humano para que su fuente de sincronización sea `master_talento_humano` activo.
5. Invocar la sincronización desde `publicar_base_maestra()` dentro de un flujo controlado y auditable.

### QAP 2 — consumidores críticos

1. Migrar Gestión Pedagógica y Gestión por Coordinador al proveedor maestro.
2. Eliminar la preferencia de `beneficiarios` en Centro de Planeación/RAM.
3. Fijar Psicosocial, Familias, Salud y Centro Documental a identificadores maestros estables.
4. Actualizar selectores de UDS, docentes, coordinadores y participantes de todos los módulos.

### QAP 3 — garantía permanente

1. Agregar `master_projection_status(fundacion_id, version_id, modulo, estado, total, fecha, error)`.
2. Crear auditoría visible “Versión maestra consumida por módulo”.
3. Incorporar una prueba E2E que cargue tres fuentes, consolide, publique y verifique todos los consumidores.
4. Añadir una compuerta de despliegue que impida SQL nuevo contra tablas heredadas para datos maestros.

## Criterios de aceptación

- Un participante nuevo aparece en todos los buscadores y selectores después de publicar, sin carga adicional.
- Un retiro deja de aparecer como activo en todos los módulos, sin borrar su historial transaccional.
- Un docente o coordinador asignado por unidad aparece en Relación del mes, Talento Humano, Gestión Pedagógica, Gestión por Coordinador, Planeación e impresiones.
- Los conteos por fundación, unidad, cargo y estado coinciden en todos los tableros.
- Cada módulo informa el mismo `version_id` maestro activo.
- Repetir la publicación/sincronización no duplica personas ni asignaciones.
- Ningún módulo usa una tabla histórica como fuente preferida de participantes o talento.

## Pruebas ejecutadas durante la auditoría

- Contrato HTTP de Base Maestra: PASS.
- Mapeo de Talento Humano en Base Maestra: PASS.
- Centro de Planeación/Psicosocial: PASS.
- Salud y Nutrición Integral: PASS.
- Gerencia BI: PASS.

Estas pruebas confirman funcionamiento local de las piezas, no propagación integral. Precisamente esa ausencia de una prueba de publicación transversal es parte del hallazgo H7.

