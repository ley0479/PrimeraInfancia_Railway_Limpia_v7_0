# Fase 12 — Centro de incidencias consultable

## Cambios realizados

- Se añadió `get_incident_center` sobre el registro transversal de errores ya existente.
- Permite listar y filtrar incidencias por identificador o estado.
- Usuarios operativos ven únicamente sus incidencias; gerente y superadministrador ven las de su fundación.
- La tarjeta presenta identificador, módulo, código, tipo, estado, severidad y fecha.
- No se devuelve el mensaje técnico, contexto interno, credenciales ni secretos.

## Archivos modificados

- `backend/modules/asistente_capacitacion/action_intents.py`
- `backend/modules/asistente_capacitacion/action_policy.py`
- `backend/modules/asistente_capacitacion/capability_registry.py`
- `backend/modules/asistente_capacitacion/routes.py`
- `backend/modules/asistente_capacitacion/tool_registry.py`
- `backend/tests/test_lia_tool_registry_v7.py`
- `backend/tests/test_liam_action_intents_v7.py`

## Archivo nuevo

- `backend/tests/test_liam_incident_center_v7.py`

## Migraciones y variables

No se requieren; se reutiliza `lia_error_incidents`.

## Pruebas realizadas

- Usuario limitado a incidentes propios.
- Gerente limitado a la fundación activa.
- Filtro de incidencias abiertas.
- Exclusión de otro tenant.
- Ausencia del mensaje técnico sanitizado en la respuesta pública.
- Regresión del orquestador, intenciones y catálogo de herramientas.

## Riesgos y pendientes

- Cambiar el estado de una incidencia será una acción separada con permiso y auditoría.
- Los identificadores históricos conservan el formato actualmente usado por el sistema.

## Rollback

Revertir el commit independiente de esta fase. No hay datos ni esquema que restaurar.
