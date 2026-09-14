# Fase 9 — Portafolio global de fundaciones y licencias

## Cambios realizados

- Se añadió `get_foundation_portfolio`, exclusivamente para `SUPERADMIN`.
- Presenta fundaciones activas, próximas a vencer, vencidas, sin usuarios y sin actividad.
- Incluye plan, fecha de vencimiento, días restantes, créditos disponibles y alerta calculada.
- El alcance global se declara explícitamente como `authorized_global`; no se confunde con una consulta tenant.
- La respuesta se renderiza mediante KPI y tabla visual del panel Liam.

## Archivos modificados

- `backend/modules/asistente_capacitacion/action_intents.py`
- `backend/modules/asistente_capacitacion/action_policy.py`
- `backend/modules/asistente_capacitacion/capability_registry.py`
- `backend/modules/asistente_capacitacion/routes.py`
- `backend/modules/asistente_capacitacion/tool_registry.py`
- `backend/tests/test_lia_tool_registry_v7.py`
- `backend/tests/test_liam_action_intents_v7.py`

## Archivo nuevo

- `backend/tests/test_liam_foundation_portfolio_v7.py`

## Migraciones y variables

No se requieren. Se reutilizan fundaciones, suscripciones, planes, usuarios y sesiones existentes.

## Pruebas realizadas

- Clasificación dinámica de vencimiento.
- Créditos bajos y agotados.
- Fundaciones sin usuarios o actividad.
- Exclusión de fundaciones eliminadas.
- Rechazo de acceso global para gerente.
- Regresión de intenciones, registro de herramientas y orquestador.

## Riesgos y pendientes

- “Sin actividad” usa la última sesión registrada; actividad técnica sin sesión no cambia ese indicador.
- Las proyecciones de consumo se incorporarán cuando exista suficiente historial comparable.

## Rollback

Revertir el commit independiente de esta fase. No existen migraciones ni datos que restaurar.
