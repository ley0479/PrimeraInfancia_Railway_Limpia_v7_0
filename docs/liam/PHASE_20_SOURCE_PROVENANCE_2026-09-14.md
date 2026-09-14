# Fase 20: fuentes y alcance verificables

## Resultado

Toda herramienta ejecutada por `LiamOrchestrator` incorpora metadatos uniformes de procedencia: fuente, alcance, fundación cuando corresponde, modo de lectura y herramienta verificadora. Las tarjetas visuales muestran esa fuente y alcance junto con los datos.

## Seguridad

- La procedencia se obtiene del catálogo interno, no del texto del modelo ni de documentos consultados.
- Las herramientas multi-tenant declaran `active_foundation` y el identificador autenticado.
- Las capacidades globales se identifican como alcance global o catálogo autorizado, sin aparentar aislamiento que no tienen.
- No se exponen consultas SQL, credenciales ni detalles internos.

## Archivos

- `backend/modules/asistente_capacitacion/orchestrator.py`
- `backend/modules/asistente_capacitacion/routes.py`
- `backend/tests/test_liam_orchestrator_core_v7.py`

## Migraciones, pruebas y rollback

No hay migraciones ni variables nuevas. Se validan contrato del orquestador, herramientas, HTTP multi-tenant, tarjetas, JavaScript y diff. El rollback consiste en revertir el commit independiente de esta fase.
