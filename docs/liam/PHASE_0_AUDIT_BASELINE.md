# LIAM — Fase 0: auditoría y baseline

Fecha: 2026-08-25  
Commit auditado: `be77958e64890778bffa621f799ec6c083ca94a3`  
Rama: `feature/motor-universal-actas-informes-capture`

## Resultado

La plataforma ya dispone de LÍA, un asistente contextual funcional y aislado. LIAM no debe duplicar esa capa de seguridad ni crear un segundo sistema de conversaciones, preferencias, auditoría o permisos. La estrategia recomendada es evolucionar la implementación existente mediante una capa visual y de interacción LIAM, conservando temporalmente los endpoints `/api/asistente-capacitacion/*` y las tablas `lia_*` para compatibilidad.

En esta fase no se modificó funcionalidad.

## Arquitectura encontrada

### Backend

- Aplicación Flask central en `backend/app.py`.
- Registro aditivo mediante `register_asistente_capacitacion(app, DATABASE_PATH)`.
- Blueprint independiente `/api/asistente-capacitacion`.
- Autorización global por sesión, rol y familia de rutas.
- Separación por `fundacion_id` obtenida del contexto autenticado.
- PostgreSQL productivo mediante la capa de compatibilidad existente.
- Migración de tablas LÍA incluida en el arranque de hosting.
- Proveedor externo deliberadamente no configurado.

### Frontend

- Inicializador: `frontend/js/modules/asistente-capacitacion.js`.
- Controladores separados de avatar, voz y ayuda.
- Estilos aislados en `frontend/css/asistente-capacitacion.css`.
- Recurso raster provisional `frontend/assets/lia/lia-human-v1.png`.
- Carga al final de `frontend/index.html`.

### Persistencia existente

- `ayuda_progreso_usuario`.
- `lia_audit_events`.
- `lia_user_preferences`.
- `lia_feedback`.

Las tablas están separadas por fundación y usuario. No se propone duplicarlas para LIAM. Un cambio de nombre físico agregaría riesgo sin aportar capacidad funcional.

## Capacidades existentes reutilizables

- Bandera maestra y banderas de texto, contexto, recorridos, voz, IA y diagnóstico.
- Contexto de rol y módulo.
- Guías institucionales para todos los módulos del menú, con contenido específico en áreas principales y fallback en las restantes.
- Presentación institucional con diseñador, fecha, versión, módulos permitidos y flujo general.
- Entrada escrita y reconocimiento de voz del navegador.
- Síntesis de voz, pausa, reanudación, detención, silencio y velocidad.
- Preferencias por usuario.
- Registro cerrado de cuatro herramientas de solo lectura.
- Redacción básica de identificadores, correos y secretos.
- Rate limit.
- Auditoría sin bloquear el flujo principal.
- Fallback estático cuando el proveedor externo no está disponible.

## Brechas frente al alcance LIAM

| Capacidad | Estado actual | Brecha |
|---|---|---|
| Identidad masculina LIAM | No implementada | El recurso actual representa a LÍA. |
| Pestaña rectangular | No implementada | El disparador actual es circular. |
| Medio cuerpo y panel integrado | Parcial | Hay panel lateral, pero el avatar es un retrato circular. |
| Máquina de estados completa | Parcial | Solo estados básicos; faltan movimiento, giro, señalamiento, teletransporte y sueño. |
| Rive/Lottie/Live2D | No disponible | Solo PNG y animaciones CSS. |
| Labios | No implementado | `speechSynthesis` cambia el estado, pero no controla boca ni visemas. |
| Tablet dinámica | No implementada | No existe un controlador ni esquema de contenido cerrado. |
| Anclajes seguros | No implementados | No hay registro de anclajes por pantalla/dispositivo. |
| Zonas seguras | No implementadas | No existe cálculo de colisiones con formularios, tablas o viewport. |
| Controles estables | No implementados | No existen `data-help-id`; el registro actual usa búsqueda heurística. |
| Caminata | No implementada | Debe permanecer desactivada hasta tener anclajes y zonas seguras. |
| Teletransportación | No implementada | Los recorridos actuales no conservan una máquina de tarea entre pantallas. |
| Spotlight y línea guía | Parcial | Existe resaltado simple, sin orquestador ni validación visual avanzada. |
| Contexto de pestaña/modal/control | No implementado | Solo se reconoce el módulo por hash/sección visible. |
| Eventos reales de recorrido | Parcial | Los pasos son principalmente narrativos; no esperan todos los eventos de negocio. |
| IA externa | Preparada, desactivada | Falta SDK, modelo, credencial de servidor, salida estructurada y validación. |
| Voz backend | No implementada | Solo reconocimiento/síntesis del navegador. |

## Riesgos principales

1. Renombrar rutas o tablas de LÍA a LIAM rompería compatibilidad sin beneficio; se debe cambiar primero la presentación pública.
2. Mantener LÍA y LIAM activos simultáneamente produciría dos asistentes, listeners y solicitudes duplicadas.
3. Activar caminata con selectores heurísticos podría señalar controles incorrectos o cubrir información.
4. El contenedor actual usa `z-index` alto y permite eventos sobre elementos resaltados; cualquier movimiento deberá preservar clics de la plataforma.
5. La imagen actual no contiene capas corporales separadas, por lo que no permite labios, manos o caminata auténticos.
6. `SpeechRecognition` depende del navegador y su servicio remoto; el permiso del micrófono no garantiza transcripción.
7. La guía específica solo cubre en profundidad un subconjunto de módulos; los demás utilizan un fallback genérico.
8. Las banderas LÍA están activas en el entorno desplegado actual. La migración debe impedir que el nuevo frontend se monte dos veces.
9. La identidad institucional procede de variables de servidor; no debe incluir documentos personales ni secretos.

## Archivos protegidos

- `backend/app.py`: solo registro mínimo de módulos.
- `frontend/js/app.js`: no incorporar lógica LIAM; únicamente eventos o adaptadores mínimos si son indispensables.
- `frontend/index.html`: solo enlaces de recursos y atributos estables localizados.
- Servicios de Base Maestra, Calendario, IDP, formatos, seguridad y multi-tenant.
- Plantillas oficiales y generadores existentes.
- Migraciones y tablas productivas existentes.

## Estrategia de migración recomendada

1. Agregar banderas `LIAM_*` sin retirar `LIA_*`.
2. Montar LIAM solamente cuando `ENABLE_LIAM_ASSISTANT=true`.
3. Si LIAM está activo, impedir el montaje visual de LÍA, pero reutilizar temporalmente su API segura.
4. Crear adaptadores independientes de avatar, estados, tablet, anclajes, zonas seguras y movimiento.
5. Registrar controles reales con `data-help-id` mediante cambios pequeños por pantalla.
6. Mantener caminata desactivada hasta superar pruebas de colisión, zoom, responsive y accesibilidad.
7. Mantener Rive/Lottie opcional; usar un SVG provisional con estados CSS verificables.
8. Desplegar inicialmente con `ENABLE_LIAM_ASSISTANT=false`.

## Baseline de pruebas

| Prueba | Resultado |
|---|---|
| LÍA contextual | PASS |
| Servicio de respuestas | PASS |
| Banderas y guías | PASS |
| Avatar humano actual | PASS |
| Preferencias y feedback | PASS |
| Fallback del proveedor | PASS |
| Registro de herramientas | PASS |
| Integridad central | PASS |
| Estabilidad responsive | PASS |
| Healthcheck Railway | PASS |

## Errores o limitaciones preexistentes

- El reconocimiento de voz puede fallar aun con permiso del micrófono debido al servicio del navegador.
- No existe recurso profesional `.riv`, Lottie o Live2D.
- La implementación actual no ofrece movimiento corporal real ni sincronización labial.
- El registro de controles no usa identificadores DOM explícitos.
- Existe un informe de auditoría de módulos sin seguimiento Git al iniciar esta fase; se conserva intacto.

## Condición para iniciar Fase 1

La Fase 1 puede comenzar sin cambiar datos productivos. Debe crear un contenedor visual LIAM independiente, desactivado por defecto, con pestaña rectangular, panel responsive, SVG provisional, estados básicos, accesibilidad y rollback por bandera.

