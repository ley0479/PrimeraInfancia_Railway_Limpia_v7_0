# Fase 39: controles del presentador de datos

## Resultado

Se conservó la sincronización existente entre voz, avatar y puntos de la tarjeta. Se añadieron controles manuales **Anterior** y **Siguiente** para recorrer indicadores o filas cuando la voz no esté activa o el usuario necesite repetir un punto.

El estado “Explicando” usa `role=status` y `aria-live=polite`. Cada punto mantiene `aria-current`, color activo, color explicado y la pose del avatar señalando a la derecha. El desplazamiento respeta la preferencia de movimiento reducido.

Se actualizaron las versiones de caché del controlador y los estilos para que el navegador cargue el comportamiento nuevo.

## Pruebas y rollback

Se validan controles, estados visuales, anuncio accesible, movimiento reducido, versiones de caché, presentador y Realtime. No hay migraciones ni cambios de datos. Para rollback, revertir el commit independiente de esta fase.
