# Fase 7 — Supervisor de entregables

## Cambios realizados

- Se añadió la herramienta de solo lectura `supervise_deliverables`.
- Compara los entregables registrados como esperados frente a los recibidos.
- Clasifica pendientes, vencidos, devueltos, incompletos y candidatos duplicados.
- Calcula cumplimiento y muestra KPI más tabla detallada en el panel visual de Liam.
- Permite filtrar por periodo y reconoce órdenes naturales de supervisión.
- Docentes y profesionales ven sus asignaciones; coordinadores ven su equipo; gerente y superadministrador permanecen limitados a la fundación activa.

## Archivos modificados

- `backend/modules/asistente_capacitacion/action_intents.py`
- `backend/modules/asistente_capacitacion/action_policy.py`
- `backend/modules/asistente_capacitacion/capability_registry.py`
- `backend/modules/asistente_capacitacion/routes.py`
- `backend/modules/asistente_capacitacion/tool_registry.py`
- `backend/tests/test_lia_tool_registry_v7.py`
- `backend/tests/test_liam_action_intents_v7.py`

## Archivo nuevo

- `backend/tests/test_liam_deliverable_supervisor_v7.py`

## Migraciones y variables

No se requieren. Se reutiliza `calendario_entregables` sin alterar su esquema.

## Pruebas realizadas

- Clasificación de recibido, pendiente, vencido, devuelto e incompleto.
- Detección de clave duplicada.
- Cálculo de cumplimiento.
- Restricción por coordinador.
- Separación entre fundaciones.
- Regresión de intenciones, herramientas y orquestador.

## Riesgos y pendientes

- “Esperado” significa entregable vigente registrado en el Calendario Inteligente; una obligación ausente del calendario no puede contarse.
- Los estados heredados deben mantenerse dentro del catálogo operativo para evitar categorías ambiguas.

## Rollback

Revertir el commit independiente de esta fase. No hay migraciones ni datos que restaurar.
