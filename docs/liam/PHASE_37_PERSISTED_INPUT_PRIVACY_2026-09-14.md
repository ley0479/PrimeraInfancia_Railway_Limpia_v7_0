# Fase 37: privacidad de entradas persistentes

## Resultado

La retroalimentación redacta correos, identificadores y credenciales antes de almacenarse. Los nombres de módulo y request ID asociados también se redactan.

Los comandos favoritos conservan referencias operativas —incluido un documento cuando el usuario decide guardar explícitamente esa búsqueda—, pero eliminan credenciales como tokens, contraseñas, secretos, API keys y encabezados de autorización. Esto preserva la función solicitada sin convertir favoritos en un depósito de credenciales.

## Pruebas y rollback

Las pruebas HTTP inspeccionan directamente las filas persistidas, verifican que no aparezcan secretos y confirman que un identificador operativo de un favorito siga siendo utilizable. Se mantienen aislamiento por usuario y tenant y ejecución mediante herramientas cerradas. No hay migraciones. Para rollback, revertir el commit independiente de esta fase.
