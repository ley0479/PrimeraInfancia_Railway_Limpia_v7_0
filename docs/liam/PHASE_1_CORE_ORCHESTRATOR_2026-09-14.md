# Fase 1 — Core y orquestador LIAM

## Cambios

- Catálogo declarativo de capacidades separado de la autoridad de ejecución.
- Orquestador central para contexto, herramienta, política, servicio y trazabilidad.
- Metadatos seguros: fuente, motor lógico, duración, módulo, tenant y `trace_id`.
- Normalización limitada de argumentos; contenido externo se conserva como datos.
- Verificación defensiva del `foundation_id` devuelto por herramientas tenant-scoped.
- Integración aditiva en el endpoint directo de herramientas, compatible con Realtime.

## Archivos

- Nuevos: `capability_registry.py`, `orchestrator.py`, prueba de contrato del Core.
- Modificado: `routes.py`.
- Migraciones: ninguna.
- Variables nuevas: ninguna.
- Endpoints nuevos: ninguno; se conserva `/api/asistente-capacitacion/tools/<tool_name>`.

## Pruebas

- Contrato catálogo/herramientas.
- Aislamiento de fundaciones.
- Trazabilidad y fuente.
- Registro de herramientas, política de acciones, Relación del Mes y HTTP multi-tenant.

## Riesgos y rollback

- El orquestador se integra primero en el endpoint usado por voz Realtime; los flujos legados de chat permanecen intactos para reducir riesgo.
- Rollback: revertir el commit de esta fase; no existen cambios de esquema ni datos.

## Pendiente siguiente

- Adoptar el orquestador en el chat determinista y multitarea después de sus pruebas de regresión.
