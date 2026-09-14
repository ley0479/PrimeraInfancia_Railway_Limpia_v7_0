# Fase 14 — Borradores de comunicaciones

## Cambios realizados

- Se añadió `prepare_communication_draft` para responsables con entregables pendientes.
- La audiencia se deriva del Calendario Inteligente; no acepta destinatarios arbitrarios del modelo.
- El borrador incluye destinatarios autorizados, UDS, pendientes, vencidos, asunto y mensaje.
- Solo superadministrador, gerente y coordinador pueden prepararlo.
- El resultado no se guarda ni se envía; declara que un envío futuro necesitará aprobación.

## Archivos modificados

- `backend/modules/asistente_capacitacion/action_intents.py`
- `backend/modules/asistente_capacitacion/action_policy.py`
- `backend/modules/asistente_capacitacion/capability_registry.py`
- `backend/modules/asistente_capacitacion/routes.py`
- `backend/modules/asistente_capacitacion/tool_registry.py`
- `backend/tests/test_lia_tool_registry_v7.py`
- `backend/tests/test_liam_action_intents_v7.py`

## Archivo nuevo

- `backend/tests/test_liam_communication_draft_v7.py`

## Migraciones y variables

No se requieren. No se conecta todavía ningún proveedor externo.

## Pruebas realizadas

- Agrupación por responsable y unidades.
- Conteo de pendientes y vencidos.
- Restricción al equipo del coordinador y a la fundación.
- Rechazo para docente.
- Confirmación de que envío y persistencia están deshabilitados.

## Riesgos y pendientes

- Correo y WhatsApp deberán conectarse mediante adaptadores separados.
- El envío exigirá vista previa, aprobación explícita, auditoría e idempotencia.

## Rollback

Revertir el commit independiente de esta fase. No existen mensajes almacenados ni enviados.
