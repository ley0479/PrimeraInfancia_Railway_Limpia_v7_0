# Fase 18: contexto y memoria temporal de sesión

## Cambios realizados

- Se agregó `lia_session_context`, separada por fundación y usuario.
- Liam conserva durante ocho horas el módulo, vista, pestaña, modal, control de ayuda, UDS, periodo, documento y tarea activa.
- El chat combina el contexto temporal previo con la pantalla actual antes de interpretar una orden.
- El módulo persistido se sustituye siempre por el módulo validado contra el rol autenticado.
- Se agregó API `GET`, `PUT` y `DELETE /api/asistente-capacitacion/session-context`.
- La memoria es minimizada: campos desconocidos, contraseñas, tokens y objetos arbitrarios no se almacenan.

## Archivos nuevos

- `backend/modules/asistente_capacitacion/context_service.py`
- `backend/migrations/migrate_liam_session_context_v7.py`
- `backend/tests/test_liam_session_context_v7.py`

## Archivos modificados

- `backend/modules/asistente_capacitacion/schema.py`
- `backend/modules/asistente_capacitacion/routes.py`
- `backend/init_hosting.py`
- `frontend/js/liam/liam-controller.js`
- `frontend/index.html`

## Migración

Migración aditiva, idempotente y registrada como `session_context` versión 1. No modifica tablas existentes.

## Pruebas y seguridad

- Filtrado estricto de campos.
- Derivación segura del periodo.
- Fusión del contexto sin reemplazar información vigente.
- Aislamiento entre fundaciones y usuarios.
- Eliminación voluntaria de memoria.
- Regresión del chat, orquestador y multi-tenant.

## Rollback

Revertir el commit de la fase. La tabla aditiva puede permanecer sin uso; eliminarla requeriría una migración destructiva independiente y no es necesario para recuperar el comportamiento anterior.
