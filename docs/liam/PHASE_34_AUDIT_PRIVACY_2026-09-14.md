# Fase 34: privacidad de auditoría y memoria

## Resultado

Se agregó redacción recursiva para diccionarios, listas y valores anidados antes de persistir metadatos de auditoría. Las claves sensibles (`token`, contraseñas, secretos, API keys y autorización) sustituyen completamente su valor.

También se redactan módulo, herramienta, request ID, campos textuales permitidos de contexto y la tarea activa. La memoria mantiene su lista cerrada de campos, aislamiento por usuario/fundación y vencimiento de ocho horas.

## Límites

La redacción minimiza exposición accidental, pero no sustituye cifrado de almacenamiento ni autoriza guardar datos sensibles. Los valores operativos numéricos y booleanos se conservan para observabilidad.

## Pruebas y rollback

Se prueban secretos anidados, correo, documento, contexto y tarea activa, incluyendo lectura directa del almacenamiento temporal. No hay migraciones. Para rollback, revertir el commit independiente de esta fase.
