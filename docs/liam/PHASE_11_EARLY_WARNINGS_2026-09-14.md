# Fase 11 — Alertas tempranas

## Cambios realizados

- Se añadió `get_early_warnings` para consolidar señales verificables del Calendario y la Base Maestra.
- Clasifica riesgos críticos, altos y preventivos.
- Detecta vencimientos, acumulación, devoluciones, entregables incompletos, duplicados, UDS inválidas y campos faltantes.
- Reutiliza los filtros por usuario, rol y fundación de los supervisores existentes.
- La interfaz utiliza expresamente “se detecta riesgo” y aclara que no son predicciones ni diagnósticos.

## Archivos modificados

- `backend/modules/asistente_capacitacion/action_intents.py`
- `backend/modules/asistente_capacitacion/action_policy.py`
- `backend/modules/asistente_capacitacion/capability_registry.py`
- `backend/modules/asistente_capacitacion/routes.py`
- `backend/modules/asistente_capacitacion/tool_registry.py`
- `backend/tests/test_lia_tool_registry_v7.py`
- `backend/tests/test_liam_action_intents_v7.py`

## Archivo nuevo

- `backend/tests/test_liam_early_warnings_v7.py`

## Migraciones y variables

No se requieren.

## Pruebas realizadas

- Priorización crítica, alta y preventiva.
- Aislamiento entre fundaciones.
- Restricción al equipo del coordinador.
- Fuente explícita de cada alerta.
- Lenguaje no predictivo y operación de solo lectura.
- Regresión de intenciones, herramientas y orquestador.

## Riesgos y pendientes

- Las alertas dependen de que fechas, estados y asignaciones estén registrados correctamente en las fuentes.
- No se ejecutan correcciones ni notificaciones automáticas.

## Rollback

Revertir el commit independiente de esta fase. No hay datos ni migraciones que restaurar.
