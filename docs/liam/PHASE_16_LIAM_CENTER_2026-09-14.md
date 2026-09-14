# Fase 16: Centro Liam

## Cambios realizados

- Se agregó la herramienta cerrada `get_liam_center`, exclusiva de `SUPERADMIN` y de solo lectura.
- El centro consolida salud, actividad, incidencias, notificaciones, fundaciones, créditos, entregables, calidad de datos y propuestas de cambio.
- Cada fuente declara su disponibilidad. Una fuente ausente degrada solamente esa sección y no bloquea toda la consulta.
- El alcance global queda declarado exclusivamente para fundaciones y propuestas administrativas; los demás bloques conservan la fundación activa.
- El chat, el canal Realtime y el panel visual reconocen el Centro Liam mediante un contrato estructurado, sin HTML generado por IA.
- Administración incluye un acceso directo que abre a Liam y ejecuta la consulta autorizada.

## Archivos modificados

- `backend/modules/asistente_capacitacion/action_intents.py`
- `backend/modules/asistente_capacitacion/action_policy.py`
- `backend/modules/asistente_capacitacion/capability_registry.py`
- `backend/modules/asistente_capacitacion/routes.py`
- `backend/modules/asistente_capacitacion/tool_registry.py`
- `backend/tests/test_lia_tool_registry_v7.py`
- `backend/tests/test_liam_action_intents_v7.py`
- `frontend/index.html`
- `frontend/js/liam/liam-controller.js`

## Archivo nuevo

- `backend/tests/test_liam_center_v7.py`

## Migraciones y variables

No requiere migración ni nuevas variables de entorno.

## Seguridad y riesgos

- El permiso se valida antes de consultar: un rol distinto de `SUPERADMIN` recibe denegación.
- No se incluyen secretos ni datos sensibles nominales en las métricas.
- El centro no ejecuta reparaciones, envíos ni modificaciones.
- Riesgo residual: las fuentes pertenecen a módulos con despliegues independientes; por eso se informa disponibilidad parcial.

## Pruebas

- Contrato del registro de herramientas.
- Detección de intención cerrada.
- Permiso exclusivo, aislamiento de actividad por fundación y degradación parcial.
- Regresión del orquestador y HTTP multi-tenant.
- Sintaxis JavaScript y verificación de espacios del diff.

## Rollback

Revertir el commit independiente de esta fase. No hay datos ni migraciones que restaurar.
