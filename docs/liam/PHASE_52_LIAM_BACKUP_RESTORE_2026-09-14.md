# Fase 52 · Restauración de backup mediante LIAM

La orden “restaura el backup N” genera una propuesta crítica; nunca restaura inmediatamente. Solo SUPERADMIN puede confirmarla y la política declara reautenticación obligatoria.

Al confirmar, el navegador solicita la contraseña directamente y la envía exclusivamente al endpoint de backups reforzado. La clave no entra al chat, al contexto de LIAM, al modelo ni a la auditoría de acciones. El servicio valida integridad y crea un backup preventivo antes de reemplazar una base SQLite; PostgreSQL continúa rechazando restauración con el servidor activo.

`restore_available=false` sigue indicando que no existe restauración automática, mientras `restore_proposal_available=true` documenta el flujo humano confirmado.

No hay migración. Se prueban intención, política, indicador de disponibilidad, ejecutor UI, separación de contraseña, caché y reautenticación HTTP. Para rollback, revertir este commit y luego la fase 51 solo si se acepta reabrir el riesgo de seguridad.
