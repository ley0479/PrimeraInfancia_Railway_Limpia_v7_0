# Fase 13 — Centro de Notificaciones

## Cambios realizados

- Se añadió `get_notification_center` con adaptadores de Planeación, Calendario, Incidencias, Documentos y Créditos.
- Unifica avisos pendientes y los ordena como críticos, advertencias o información.
- Respeta destinatario, rol, usuario y fundación.
- Usuarios operativos solo reciben documentos propios; gerente y superadministrador pueden consultar los de su fundación.
- La respuesta no marca, envía ni modifica notificaciones.
- Cada fuente declara si estuvo disponible para evitar presentar ausencia técnica como cero confirmado.

## Archivos modificados

- `backend/modules/asistente_capacitacion/action_intents.py`
- `backend/modules/asistente_capacitacion/action_policy.py`
- `backend/modules/asistente_capacitacion/capability_registry.py`
- `backend/modules/asistente_capacitacion/routes.py`
- `backend/modules/asistente_capacitacion/tool_registry.py`
- `backend/tests/test_lia_tool_registry_v7.py`
- `backend/tests/test_liam_action_intents_v7.py`

## Archivo nuevo

- `backend/tests/test_liam_notification_center_v7.py`

## Migraciones y variables

No se requieren. Se consultan las fuentes existentes mediante adaptadores tolerantes a módulos opcionales.

## Pruebas realizadas

- Integración de cinco fuentes.
- Priorización de avisos.
- Destinatario individual y aviso general.
- Documento e incidencia limitados al usuario.
- Exclusión de otro usuario y otro tenant.
- Operación estrictamente de solo lectura.

## Riesgos y pendientes

- Una fuente marcada como no disponible requiere revisión técnica; no se interpreta como “sin notificaciones”.
- Marcar como leído o enviar comunicaciones requerirá una acción confirmada separada.

## Rollback

Revertir el commit independiente de esta fase. No hay datos ni esquema que restaurar.
