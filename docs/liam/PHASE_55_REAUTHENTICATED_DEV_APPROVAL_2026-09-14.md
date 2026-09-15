# Fase 55 · Aprobación ADMIN/DEV reautenticada

La evidencia satisfactoria de un sandbox puede aprobarse mediante `POST /api/asistente-capacitacion/dev/change-requests/<request_id>/approve`. El endpoint exige simultáneamente sesión SUPERADMIN, fundación y usuario propietarios, texto literal `APROBAR CAMBIO`, contraseña actual y checksum del resultado vigente.

Una aprobación crea dos artefactos tenant-scoped:

- `APPROVAL`: identidad interna del aprobador, fecha y checksum exacto de plan/resultado;
- `ROLLBACK_PLAN`: commit base reportado, rutas afectadas y estrategia limitada al futuro commit aprobado.

La solicitud cambia a `APPROVED` y la compuerta Aprobación queda `READY`. Despliegue permanece `DISABLED`: este flujo no aplica el diff, no crea commits, no ejecuta rollback y no despliega.

## Pruebas

`test_liam_dev_change_approval_http_v7.py` valida contraseña, confirmación, checksum, estado satisfactorio, aislamiento por usuario/fundación, rol, doble aprobación, auditoría y plan de rollback. Las regresiones de plan, resultado firmado y revisión también permanecen verdes.

## Rollback

Revertir el commit de la fase elimina el endpoint y servicio de aprobación. No hay migración nueva. Los artefactos aditivos existentes quedan inertes; en ningún momento se modificó código desde el flujo ADMIN/DEV.
