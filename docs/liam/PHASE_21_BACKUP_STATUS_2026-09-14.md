# Fase 21: estado sanitizado de copias de seguridad

## Resultado

Liam puede informar a `SUPERADMIN` cuántas copias existen, cuántas son válidas o presentan error y los metadatos no sensibles de la última copia. La información también aparece en el Centro Liam.

## Seguridad

- No devuelve nombre de archivo, ruta, hash, base de datos ni credenciales.
- Es una herramienta global explícita y exclusiva de `SUPERADMIN`.
- Es de solo lectura y no permite restaurar ni crear copias.
- Una restauración futura continuará requiriendo permiso elevado y confirmación reforzada.

## Archivos

Se modifican el catálogo, la política, intenciones, herramienta, Centro Liam, contrato visual, voz y pruebas. Se agrega `test_liam_backup_status_v7.py`.

## Migraciones y rollback

No hay migraciones ni variables nuevas. La fase reutiliza `backups_sistema`. Para rollback, revertir el commit independiente de esta fase.
