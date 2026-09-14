# Fase 45 · Accesibilidad del historial de acciones

La vista administrativa anuncia carga y resultados mediante `role=status`, `aria-live` y `aria-busy`. El botón declara el panel controlado, la tabla incluye un título accesible y cada encabezado usa `scope=col`.

No cambia permisos, datos, colores ni distribución visual. No requiere migración. La prueba estática verifica los atributos y conserva el render seguro con `textContent`. Para rollback, revertir este commit.
