# Fase 3 — Búsqueda universal

## Cambios

- Herramienta cerrada `universal_search` para Base Maestra, usuarios, talento, UDS y Centro Documental.
- Búsqueda por nombre, documento, referencia, UDS, docente, rol, periodo, estado o ID disponible.
- Paginación con máximo de 50 resultados y respuesta visual con fuente.
- Filtro `fundacion_id` obligatorio en cada fuente; sin teléfonos, direcciones, credenciales ni SQL generado por IA.
- Disponible en texto y voz Realtime mediante el orquestador y la política de permisos.

## Impacto

- Sin migraciones, endpoints nuevos ni variables.
- Se amplían catálogo, política, intención, herramienta y serializador visual.
- Rollback: revertir el commit de esta fase.

## Pruebas

- Búsqueda y paginación.
- Exclusión de registros pertenecientes a otra fundación.
- Ausencia de campos sensibles.
- Regresión de catálogo, Core, Base Maestra y HTTP multi-tenant.
