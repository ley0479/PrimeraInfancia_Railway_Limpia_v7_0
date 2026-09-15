# Fase 53 · Plan verificable de sandbox ADMIN/DEV

SUPERADMIN puede pedir el plan de sandbox de una solicitud `DEV-*`. LIAM genera y persiste un artefacto firmado con SHA-256 que contiene objetivo, archivos permitidos por registro cerrado, riesgo, pruebas, rutas prohibidas, reglas de aislamiento y rollback.

El plan cambia la solicitud a `PLANNED` y las compuertas de arquitectura/riesgo a `READY`; pruebas quedan `PLANNED`. No genera comandos, no modifica código, no usa red, no despliega y exige un runner aislado externo para continuar.

## Migración

`migrate_liam_dev_artifacts_v7.py` agrega `lia_dev_change_artifacts` e índice tenant/usuario/solicitud. No altera solicitudes existentes.

## Pruebas y rollback

Se verifican checksum, regeneración idempotente, archivos/rutas cerrados, estado, tarjeta, rol, usuario y tenant. Para rollback, revertir el commit; la tabla aditiva puede conservarse sin efecto funcional.
