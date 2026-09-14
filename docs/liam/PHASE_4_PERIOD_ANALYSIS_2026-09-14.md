# Fase 4 — Comparación segura entre periodos

## Cambios realizados

- Se registró `compare_periods` en el orquestador, la política de permisos y Realtime.
- Liam reconoce órdenes como “compara agosto contra septiembre de 2026”.
- La consulta usa el último cruce existente de cada periodo y filtra obligatoriamente por la fundación de la sesión.
- El panel visual presenta una tabla con valor anterior, valor actual, variación y disponibilidad.
- Si falta un periodo, Liam no estima valores y lo declara expresamente.

## Archivos modificados

- `backend/modules/asistente_capacitacion/action_intents.py`
- `backend/modules/asistente_capacitacion/action_policy.py`
- `backend/modules/asistente_capacitacion/capability_registry.py`
- `backend/modules/asistente_capacitacion/routes.py`
- `backend/modules/asistente_capacitacion/tool_registry.py`
- `backend/tests/test_lia_tool_registry_v7.py`
- `backend/tests/test_liam_action_intents_v7.py`

## Archivo nuevo

- `backend/tests/test_liam_period_comparison_v7.py`

## Migraciones y variables

No se requieren migraciones ni variables de entorno. Se reutiliza `cb_cruces` sin modificar su estructura.

## Pruebas realizadas

- Comparación de dos periodos reales.
- Ausencia de uno de los periodos sin inferencias.
- Separación entre dos fundaciones con cifras deliberadamente diferentes.
- Registro coherente entre capacidades y herramientas.
- Regresión de intenciones, orquestador y contrato HTTP multi-tenant.

Resultado: todas las pruebas ejecutadas finalizaron correctamente.

## Riesgos y pendientes

- La comparación refleja los cruces mensuales disponibles, no una reconstrucción histórica de la Base Maestra.
- Quedan por incorporar más indicadores cuando exista una fuente histórica versionada y verificable para ellos.

## Rollback

Revertir el commit independiente de esta fase. No hay datos ni esquema que restaurar.
