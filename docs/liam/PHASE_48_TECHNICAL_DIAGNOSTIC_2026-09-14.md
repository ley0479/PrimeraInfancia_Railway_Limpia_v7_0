# Fase 48 · Diagnóstico técnico elevado

SUPERADMIN puede solicitar por ID exacto una vista técnica sanitizada de una incidencia dentro de la fundación activa. La tarjeta separa módulo, operación, HTTP, código, estado, excepción sanitizada y traza.

La herramienta vuelve a redactar credenciales, documentos y correos; descarta claves de contexto no permitidas y mantiene `cross_foundation=false`. Otros roles reciben denegación del Permission Gateway.

No requiere migración. Se verifican rol, tenant, redacción, intención y catálogo cerrado. Para rollback, revertir este commit.
