# Fase 17: chat unificado con el orquestador Liam

## Resultado

Las herramientas cerradas solicitadas desde el chat y los planes de lectura multitarea pasan por `LiamOrchestrator`. Se elimina la ejecución directa heredada en esos dos recorridos sin alterar sus mensajes ni componentes visuales.

## Controles aplicados

- Normalización de argumentos como datos.
- Comprobación del catálogo de capacidades.
- Validación de alcance institucional declarado.
- Telemetría uniforme con `trace_id`, motor y duración.
- Auditoría por cada herramienta y por cada paso multitarea.

## Archivo modificado

- `backend/modules/asistente_capacitacion/routes.py`

## Migraciones y variables

No requiere migraciones ni variables nuevas.

## Pruebas

- Contrato del orquestador y aislamiento institucional.
- Contrato de herramientas e intenciones.
- Regresión HTTP multi-tenant.
- Sintaxis JavaScript y verificación del diff.

## Riesgo y rollback

Riesgo bajo: se conserva el mismo registro de herramientas y las mismas funciones de servicio. Revertir el commit de esta fase restaura la invocación directa anterior.
