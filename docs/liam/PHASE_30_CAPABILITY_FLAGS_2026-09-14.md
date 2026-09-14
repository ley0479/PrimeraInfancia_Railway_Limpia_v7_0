# Fase 30: feature flags granulares

## Resultado

Se agregaron las banderas públicas `LIAM_VISUAL_PANEL_ENABLED`, `LIAM_SEARCH_ENABLED`, `LIAM_ACTIONS_ENABLED`, `LIAM_ADMIN_ENABLED`, `LIAM_DEV_ENABLED` y `LIAM_REPAIR_ENABLED`. Todas dependen primero de `ENABLE_LIAM_ASSISTANT`.

ADMIN/DEV tiene una compuerta backend efectiva y permanece apagado por defecto. Aunque un cliente construya manualmente una petición, no podrá registrar, listar ni revisar solicitudes técnicas hasta que el servidor habilite `LIAM_DEV_ENABLED=true`.

Las capacidades compatibles existentes de panel, búsqueda, acciones y consultas administrativas conservan su valor predeterminado. Reparaciones y ADMIN/DEV permanecen apagadas para activación controlada.

## Pruebas y rollback

Se validan valores predeterminados, dependencia de la bandera principal, activación explícita, variables documentadas y presencia de la compuerta servidor. No hay migraciones. Para rollback, revertir el commit independiente de esta fase.
