# Fase 27: solicitudes ADMIN/DEV controladas

## Resultado

`SUPERADMIN` puede pedir a Liam que registre una solicitud técnica. Se guarda como `DRAFT` con módulo, objetivo sanitizado, impacto y flujo obligatorio: auditoría, propuesta, sandbox, pruebas, diff, aprobación y despliegue manual.

## Controles

- Registrar la solicitud no modifica código.
- No ejecuta pruebas, procesos del sistema ni despliegues.
- Solo acepta módulos registrados.
- Redacta secretos antes de persistir.
- Listado aislado por fundación y usuario solicitante.
- Acceso exclusivo de `SUPERADMIN`.

## Migración

Se agrega de forma aditiva e idempotente `lia_dev_change_requests`, con versión de esquema y ejecución en predeploy.

## Pruebas y rollback

Se comprueban sanitización, rol, aislamiento por tenant y usuario, estado borrador y ausencia de ejecución. Para rollback, revertir el commit; la tabla aditiva puede permanecer sin uso.
