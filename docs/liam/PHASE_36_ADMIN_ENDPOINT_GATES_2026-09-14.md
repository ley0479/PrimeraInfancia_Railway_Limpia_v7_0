# Fase 36: compuertas de endpoints administrativos

## Resultado

`LIAM_ADMIN_ENABLED` controla ahora las rutas administrativas propias del asistente:

- auditoría de conversaciones;
- listado administrativo de incidencias;
- modificación de configuración visual;
- catálogo de adaptadores de notificación.

La lectura de apariencia permanece disponible para que todos los roles puedan renderizar el asistente, pero solo roles autorizados pueden editarla. El catálogo de proveedores requiere además `SUPERADMIN`; no expone credenciales ni permite envíos.

## Pruebas y rollback

Se prueban bandera apagada, SUPERADMIN, rechazo de DOCENTE y lectura no editable de configuración visual. Los valores predeterminados mantienen compatibilidad. No hay migraciones. Para rollback, revertir el commit independiente de esta fase.
