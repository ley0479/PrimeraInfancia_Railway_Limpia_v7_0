# Fase 6 — Constructor seguro de reportes personalizados

## Cambios realizados

- Se añadió `build_custom_report_preview` al orquestador, permisos y herramientas Realtime.
- Liam reconoce solicitudes como “crea un reporte con unidad, docente y número de niños”.
- Se ofrecen tres reportes cerrados: cobertura por unidad, distribución etaria y cobertura por coordinador.
- Los campos se seleccionan de un catálogo fijo; no se acepta HTML ni SQL producido por la IA.
- La respuesta se muestra como tabla visual y se identifica como vista previa de solo lectura.
- Docentes y coordinadores reciben únicamente registros asignados a su identidad; los demás roles autorizados permanecen limitados a la fundación activa.

## Archivos modificados

- `backend/modules/asistente_capacitacion/action_intents.py`
- `backend/modules/asistente_capacitacion/action_policy.py`
- `backend/modules/asistente_capacitacion/capability_registry.py`
- `backend/modules/asistente_capacitacion/routes.py`
- `backend/modules/asistente_capacitacion/tool_registry.py`
- `backend/tests/test_lia_tool_registry_v7.py`
- `backend/tests/test_liam_action_intents_v7.py`

## Archivo nuevo

- `backend/tests/test_liam_safe_report_builder_v7.py`

## Migraciones y variables

No se requieren. La herramienta consulta la Base Maestra activa mediante consultas parametrizadas predefinidas.

## Pruebas realizadas

- Selección de campos permitidos.
- Rechazo de un campo sensible no registrado.
- Rechazo de SQL como tipo de reporte.
- Aislamiento entre fundaciones.
- Restricción de coordinador a sus registros asignados.
- Regresión del orquestador y registro de herramientas.

Resultado: todas las pruebas ejecutadas finalizaron correctamente.

## Riesgos y pendientes

- La vinculación por responsable exige que el nombre del perfil coincida con el nombre consolidado en Base Maestra.
- La exportación será una acción separada y confirmada; esta fase únicamente genera vista previa.

## Rollback

Revertir el commit independiente de esta fase. No hay datos ni esquema que restaurar.
