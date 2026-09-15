# Fase 51 · Reautenticación para restaurar backups

El restaurador existente conserva la autorización exclusiva de SUPERADMIN y ahora exige simultáneamente la palabra `RESTAURAR` y la contraseña actual del usuario autenticado.

El servidor localiza el hash por usuario y fundación activos, valida con Werkzeug y nunca persiste ni audita la contraseña. Solo registra éxito o fallo de reautenticación. La interfaz solicita la contraseña después de la advertencia destructiva.

No hay migración. La prueba HTTP usa una base temporal, valida rechazo por ausencia/error, aceptación de una clave correcta y ausencia de contraseñas en auditoría. No restaura datos reales. Para rollback, revertir este commit; hacerlo reabriría una operación crítica sin reautenticación.
