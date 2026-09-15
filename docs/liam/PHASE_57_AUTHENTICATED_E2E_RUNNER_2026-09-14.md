# Fase 57 · Runner E2E autenticado de solo lectura

`tools/liam_authenticated_e2e.py` inicia sesión con una cuenta de prueba recibida exclusivamente por variables de entorno y consulta mediante GET los contratos de autenticación, Base Maestra, unidades, calendario, entregables, salud/nutrición, Motor de Plantillas, RPP, RAM, RAN, RRAN, Centro Documental, facturación, usuarios, fundaciones, formatos, LIAM, backups y Bienestarina. Las sondas RPP/RAN/RRAN usan entradas deliberadamente incompletas o inexistentes y verifican su rechazo controlado, sin generar archivos.

El informe guarda solamente host, rol, fundación, código HTTP, duración, claves superiores de la respuesta y trace ID. Nunca persiste usuario, contraseña, token, cookies ni contenido institucional. Solo admite HTTPS remoto; HTTP queda limitado a localhost. No contiene solicitudes de escritura.

`test_liam_authenticated_e2e_runner_v7.py` verifica que, después del login, todas las operaciones son GET, que los secretos no llegan al reporte y que las URL inseguras son rechazadas.

La ejecución contra el entorno objetivo continúa pendiente hasta disponer de URL y credenciales de una cuenta de prueba autorizada. No se utilizará una cuenta real ni se intentará eludir autenticación.

## Rollback

Revertir el commit elimina el runner y sus variables documentadas. La aplicación productiva no importa esta herramienta y no cambia su comportamiento.
