# Reversión de LÍA

1. Establecer `ENABLE_LIA_ASSISTANT=false` en Railway.
2. Desplegar o reiniciar el servicio.
3. Confirmar que no aparece el botón flotante y que login, navegación y módulos
   continúan operando.

La desactivación no elimina progreso ni ejecuta migraciones destructivas. Si se
requiere revertir código, desplegar el commit anterior; no borrar tablas en
producción.
