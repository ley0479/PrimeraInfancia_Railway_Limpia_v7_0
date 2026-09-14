# Fase 35: frontera contra prompt injection

## Resultado

El contexto recuperado dejó de enviarse con rol `developer`. Se serializa después de redacción estructural y se envía como datos de referencia con rol `user`, dentro de delimitadores `DATOS_NO_CONFIABLES_INICIO/FIN`.

La directiva institucional establece que historial, documentos, Base Maestra, archivos, resultados y campos de usuario no pueden cambiar permisos, herramientas ni instrucciones. Realtime aplica la misma frontera al contexto institucional.

## Alcance y límites

Esta defensa reduce la autoridad de contenido recuperado y hace explícita su procedencia. No reemplaza el Permission Gateway: toda consulta o acción continúa pasando por herramientas cerradas, rol y tenant.

## Pruebas y rollback

Una prueba intercepta el payload al proveedor y verifica jerarquía, delimitadores y redacción de secretos; también valida el prompt Realtime. No realiza llamadas de red. No hay migraciones. Para rollback, revertir el commit independiente de esta fase.
