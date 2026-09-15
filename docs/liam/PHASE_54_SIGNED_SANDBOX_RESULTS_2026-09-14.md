# Fase 54 · Resultados firmados del sandbox ADMIN/DEV

Se agregó un canal HTTP exclusivo de SUPERADMIN para recibir evidencia producida por un runner externo aislado. El cuerpo exacto se autentica con HMAC-SHA256 mediante `LIAM_DEV_SANDBOX_SIGNING_KEY`; la clave nunca se devuelve al cliente ni se almacena en la base de datos.

## Contrato

`POST /api/asistente-capacitacion/dev/sandbox-results/<request_id>` acepta como máximo 256 KiB y valida:

- solicitud, fundación y usuario de la sesión activa;
- checksum del plan vigente;
- diff unificado de hasta 120 KiB;
- rutas limitadas a los archivos del plan y a su prueba generada;
- resultado de `git diff --check`;
- exactamente todas las pruebas autorizadas, sin duplicados;
- firma HMAC con comparación resistente a temporización.

El resultado queda como artefacto `SANDBOX_RESULT` con SHA-256 y estado `PASSED` o `FAILED`. La revisión solo habilita las compuertas Pruebas y Diff cuando toda la evidencia es satisfactoria. Aprobación continúa pendiente y Despliegue permanece deshabilitado.

## Seguridad y operación

El servidor de la plataforma no ejecuta comandos, no aplica el diff, no escribe en archivos de código, no inicia despliegues y no acepta rutas fuera del registro. La variable nueva queda vacía por defecto; sin ella el endpoint responde 503.

## Pruebas

`test_liam_dev_sandbox_result_http_v7.py` verifica resultado válido, auditoría, compuertas, aislamiento por usuario y tenant, rol, firma alterada, checksum obsoleto, ruta prohibida y conjunto incompleto de pruebas. También se ejecutaron las regresiones de plan, revisión ADMIN/DEV y feature flags.

## Rollback

Revertir el commit de esta fase elimina el endpoint y su validador. No existe migración nueva: se reutiliza la tabla aditiva de artefactos de la fase 53. Los artefactos ya guardados quedan inertes y no modifican código productivo.
