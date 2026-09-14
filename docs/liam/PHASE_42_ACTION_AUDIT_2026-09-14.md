# Fase 42 · Auditoría estructurada de acciones

Se agregó `liam_action_audit` como registro aditivo e independiente del historial general. Conserva tenant, usuario, sesión, traza, intención, acción solicitada/autorizada, riesgo, recurso y resultado del ciclo.

Las propuestas confirmables se registran antes de ejecutarse. Los eventos del ejecutor cliente actualizan únicamente una fila coincidente por fundación, usuario, traza y acción. No se guardan argumentos libres ni datos sensibles; los estados anterior y posterior permanecen vacíos hasta que un ejecutor servidor confiable pueda suministrarlos.

## Migración

`backend/migrations/migrate_liam_action_audit_v7.py` crea tabla, índice y versión de esquema de forma aditiva. No elimina ni transforma datos existentes.

## Pruebas y rollback

Se verifican ciclo propuesto/completado, aislamiento de tenant y usuario, y ausencia de parámetros sensibles. Para rollback funcional se revierte el commit; la tabla puede conservarse sin afectar compatibilidad. Su eliminación física requiere una migración posterior aprobada.
