# Fase 32: compuertas de guía y recorridos

## Resultado

Las banderas existentes de ayuda contextual, recorridos y presentación ahora se verifican también en sus endpoints backend:

- `/contexto` exige ayuda contextual habilitada.
- `/progreso` exige recorridos guiados habilitados.
- `/presentation` exige presentación institucional habilitada.
- El recorrido general y su progreso exigen `LIAM_TOURS_ENABLED` y `ELIAN_PLATFORM_TOUR_ENABLED`.

Esto evita que una interfaz antigua o una petición manual utilice capacidades que el servidor desactivó. El manual operativo permanece accesible porque es documentación institucional y no depende de animaciones ni recorridos.

## Pruebas y rollback

La prueba HTTP apaga cada bandera y verifica respuestas 404, además de conservar el fallback textual del chat. Las regresiones con valores predeterminados comprueban que los recorridos existentes siguen funcionando. No hay migraciones. Para rollback, revertir el commit independiente de esta fase.
