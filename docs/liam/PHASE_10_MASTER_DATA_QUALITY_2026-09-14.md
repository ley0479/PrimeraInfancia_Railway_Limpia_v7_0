# Fase 10 — Calidad de Base Maestra

## Cambios realizados

- Se añadió `analyze_master_data_quality` como diagnóstico de solo lectura.
- Detecta grupos de documentos duplicados, exceso de registros, campos obligatorios faltantes, beneficiarios con UDS inexistente, unidades sin responsable y docentes sin unidad.
- Consulta las inconsistencias abiertas ya registradas por el sistema.
- Docente y coordinador quedan limitados a sus asignaciones; los demás roles autorizados, a la fundación activa.
- La respuesta visual contiene KPI y hallazgos agregados, sin documentos ni nombres personales.
- La herramienta declara que no realiza correcciones automáticas.

## Archivos modificados

- `backend/modules/asistente_capacitacion/action_intents.py`
- `backend/modules/asistente_capacitacion/action_policy.py`
- `backend/modules/asistente_capacitacion/capability_registry.py`
- `backend/modules/asistente_capacitacion/routes.py`
- `backend/modules/asistente_capacitacion/tool_registry.py`
- `backend/tests/test_lia_tool_registry_v7.py`
- `backend/tests/test_liam_action_intents_v7.py`

## Archivo nuevo

- `backend/tests/test_liam_master_quality_v7.py`

## Migraciones y variables

No se requieren. Se reutilizan las tablas maestras e inconsistencias existentes.

## Pruebas realizadas

- Duplicados dentro de la fundación y responsable autorizado.
- Campos faltantes y UDS inexistente.
- Docente sin unidad.
- Exclusión de otro coordinador y otra fundación.
- Resultado agregado sin documentos personales.
- Regresión de intenciones, herramientas y orquestador.

## Riesgos y pendientes

- NUI se consolida en el campo canónico `documento`; no se inventa un segundo identificador.
- Resolver un hallazgo seguirá requiriendo la acción humana dentro del módulo fuente.

## Rollback

Revertir el commit independiente de esta fase. No existen cambios de esquema ni datos que restaurar.
