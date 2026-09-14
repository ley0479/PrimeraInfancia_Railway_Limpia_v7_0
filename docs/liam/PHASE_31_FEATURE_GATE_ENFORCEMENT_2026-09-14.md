# Fase 31: aplicación efectiva de feature flags

## Resultado

Las banderas granulares dejaron de ser únicamente declarativas. El backend aplica una compuerta común antes de ejecutar herramientas desde chat multitarea, chat normal y endpoint de herramientas usado por voz/Realtime.

- `LIAM_SEARCH_ENABLED` controla búsqueda universal, perfiles y beneficiarios.
- `LIAM_ACTIONS_ENABLED` controla propuestas y borradores operativos y también la confirmación servidor.
- `LIAM_ADMIN_ENABLED` controla salud, backups, uso, portafolio y Centro Liam.
- `LIAM_DEV_ENABLED` controla solicitudes y revisiones ADMIN/DEV.
- `LIAM_REPAIR_ENABLED` controla la publicación del registro de reparaciones y sus propuestas.
- `LIAM_VISUAL_PANEL_ENABLED` conserva el texto pero suprime tablas y datos visuales cuando está apagada.

El catálogo `/tools` y la lista enviada a Realtime omiten capacidades desactivadas, además de rechazarlas en ejecución. Esto impide confiar únicamente en la interfaz.

## Compatibilidad y seguridad

Los valores predeterminados de búsqueda, acciones y administración siguen habilitados cuando LIAM está activo. ADMIN/DEV y reparaciones continúan apagados por defecto. La plataforma permanece operativa si cualquier capacidad se desactiva.

## Pruebas y rollback

La prueba HTTP comprueba catálogo filtrado, respuestas 403, reparaciones ocultas y fallback textual cuando el panel visual está apagado. No hay migraciones. Para rollback, revertir el commit independiente de esta fase.
