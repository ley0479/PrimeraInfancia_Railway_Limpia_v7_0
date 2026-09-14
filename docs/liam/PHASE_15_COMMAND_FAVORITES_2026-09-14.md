# Fase 15 — Comandos favoritos persistentes

## Cambios realizados

- Se añadió almacenamiento por fundación y usuario para comandos favoritos.
- Guardar un favorito nuevo no reemplaza los demás; el mismo nombre actualiza únicamente ese favorito del mismo usuario.
- Se añadieron endpoints para listar, guardar/actualizar y eliminar favoritos propios.
- “Liam ejecuta Pendientes docentes” resuelve el favorito del usuario autenticado.
- Las consultas de solo lectura se ejecutan mediante el registro seguro de herramientas.
- Las acciones mutables nunca se ejecutan directamente y conservan su confirmación y permisos originales.
- Todas las operaciones de mantenimiento quedan auditadas.
- El panel permite guardar la última orden, consultar favoritos, ejecutarlos y eliminarlos.

## Migración

- `backend/migrations/migrate_liam_command_favorites_v7.py`
- Aditiva, idempotente y conectada al predeploy en `backend/init_hosting.py`.
- Crea `lia_command_favorites` y registra la versión del componente.

## Archivos modificados

- `backend/init_hosting.py`
- `backend/modules/asistente_capacitacion/schema.py`
- `backend/modules/asistente_capacitacion/routes.py`
- `backend/modules/asistente_capacitacion/action_intents.py`
- `backend/modules/asistente_capacitacion/action_policy.py`
- `backend/modules/asistente_capacitacion/capability_registry.py`
- `backend/modules/asistente_capacitacion/tool_registry.py`
- pruebas del catálogo e intenciones.

## Pruebas realizadas

- Migración ejecutada dos veces.
- Dos favoritos conservados simultáneamente.
- Actualización por nombre sin duplicar.
- Separación entre usuarios y fundaciones.
- Eliminación ajena rechazada.
- Ejecución de lectura segura y retención de confirmación para RAM.

## Riesgos y pendientes

- Cambiar permisos después de guardar un favorito se respeta al ejecutarlo.

## Rollback

Revertir el commit. La tabla puede conservarse sin afectar versiones anteriores; eliminarla requiere una migración destructiva separada y no se recomienda.
