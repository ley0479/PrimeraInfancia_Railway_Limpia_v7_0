# Reporte de implementación LIAM

## Resumen

Se implementó una primera versión modular y reversible de LIAM sobre la infraestructura segura de LÍA. Permanece desactivada por defecto. Incluye identidad visual, pestaña rectangular, panel responsive, estados, holograma, tablet, voz reutilizada, resaltado, controles y anclajes cerrados, teletransporte, recorrido institucional inicial, movimiento reducido y fallback estático.

## Archivos y riesgo

| Área | Acción | Riesgo |
|---|---|---|
| Configuración backend | Banderas `LIAM_*` aditivas | Bajo |
| Endpoint de configuración | Agrega objeto `liam` sin retirar `lia` | Bajo |
| Respuesta del asistente | Agrega comandos visuales estructurados | Bajo |
| Frontend LIAM | Nuevos módulos independientes | Bajo con bandera apagada |
| Frontend LÍA | Evita montaje doble cuando LIAM está activo | Bajo |
| Voz compartida | Sincroniza estados LIAM | Bajo |
| HTML | Carga controlador y dos `data-help-id` | Bajo |
| Imagen | Póster generado provisional | Visual |

## Funciones implementadas

- Pestaña lateral rectangular y panel lateral/inferior.
- Personaje masculino LIAM con uniforme, audífono, tablet y base holográfica.
- Estados cerrados y transiciones básicas CSS.
- Registro cerrado de controles y anclajes.
- Motor inicial de zonas seguras.
- Teletransporte y caminata condicionada por bandera/dispositivo.
- Resaltado sin bloquear clics.
- Tablet con tipos permitidos.
- Presentación institucional por rol.
- Preguntas escritas y voz existente.
- Lip sync básico desacoplado.
- Recorrido del panel por seis áreas.
- Movimiento reducido y responsive.
- Carga diferida del runtime cuando LIAM está habilitado.

## Anclajes implementados

| Anclaje | Pantalla | Dispositivos |
|---|---|---|
| `liam.panel.home` | Global | Todos |
| `liam.anchor.dashboard.cuentame` | Panel | Escritorio/tablet |
| `liam.anchor.dashboard.talent-human` | Panel | Escritorio/tablet |
| `liam.anchor.dashboard.nutrition` | Panel | Escritorio/tablet |
| `liam.anchor.dashboard.calendar` | Panel | Escritorio/tablet |
| `liam.anchor.dashboard.document-engine` | Panel | Escritorio/tablet |
| `liam.anchor.dashboard.formats` | Panel | Escritorio/tablet |

## Pruebas

Las 11 pruebas seleccionadas pasaron: contrato LIAM, siete contratos LÍA, integridad, responsive y healthcheck Railway. Todos los JavaScript LIAM superaron `node --check`.

El validador integral de release no terminó por condiciones preexistentes: manifiesto de hashes desactualizado, artefactos runtime/cachés presentes y Bash no accesible. La sintaxis Python y JSON sí pasó antes de la interrupción.

## Seguridad

No se agregaron escrituras operativas. LIAM reutiliza autenticación, tenant, rol, rate limit, redacción y herramientas de solo lectura. Los movimientos, controles, anclajes, estados y contenidos de tablet usan registros cerrados.

## Pendientes reales

- Recurso profesional Rive/Lottie/Live2D.
- Transparencia alfa real del recurso definitivo; el póster actual integra fondo oscuro.
- Movimiento corporal y labios por capas.
- Visemas avanzados y voz backend.
- Adaptadores de pestaña/modal/control activo.
- Anclajes para el resto de pantallas.
- Recorridos guiados que esperen todos los eventos reales de negocio.
- Pruebas E2E visuales en navegadores y dispositivos físicos.
- Piloto multi-tenant en producción.

No se declaran completas estas funciones pendientes.

## Railway y activación

Desplegar inicialmente con `ENABLE_LIAM_ASSISTANT=false`. No activar caminata, voz, lip sync, IA ni tiempo real. Después del healthcheck se puede habilitar la interfaz en un tenant piloto. Los valores secretos no forman parte de este informe.

## Rollback

Establecer `ENABLE_LIAM_ASSISTANT=false`. La interfaz anterior de LÍA puede seguir disponible con su bandera existente. No es necesario borrar ni revertir tablas.

