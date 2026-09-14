# Fase 8 — Salud del sistema sanitizada

## Cambios realizados

- Se añadió `get_system_health`, disponible exclusivamente para `SUPERADMIN`.
- Verifica conectividad de base y disponibilidad de auditoría LIAM, Motor Documental, Calendario y Base Maestra.
- Devuelve estados `OPERATIVO` o `DEGRADADO` en una tarjeta visual.
- Cuenta eventos fallidos únicamente dentro de la fundación activa.
- El resultado declara explícitamente su sanitización y no incluye configuración, rutas ni secretos.

## Archivos modificados

- `backend/modules/asistente_capacitacion/action_intents.py`
- `backend/modules/asistente_capacitacion/action_policy.py`
- `backend/modules/asistente_capacitacion/capability_registry.py`
- `backend/modules/asistente_capacitacion/routes.py`
- `backend/modules/asistente_capacitacion/tool_registry.py`
- `backend/tests/test_lia_tool_registry_v7.py`
- `backend/tests/test_liam_action_intents_v7.py`

## Archivo nuevo

- `backend/tests/test_liam_system_health_v7.py`

## Migraciones y variables

No se requieren.

## Pruebas realizadas

- Componentes operativos.
- Conteo de fallos aislado por tenant.
- Rechazo para un docente.
- Ausencia de nombres de secretos y configuración sensible.
- Regresión de intenciones, política, herramientas y orquestador.

## Riesgos y pendientes

- El diagnóstico comprueba disponibilidad transaccional, no sustituye monitoreo externo de infraestructura.
- Almacenamiento, colas y proveedores externos se agregarán mediante adaptadores cuando estén configurados.

## Rollback

Revertir el commit independiente de esta fase. No existen datos ni migraciones que restaurar.
