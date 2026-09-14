# Fase 49 · Ciclo administrativo de incidencias

Gerencia y SUPERADMIN pueden ordenar un cambio de estado mediante lenguaje natural. LIAM crea una propuesta de 60 segundos, no modifica la incidencia hasta recibir confirmación y garantiza consumo único.

Las transiciones válidas están cerradas por estado. Resolver o cerrar exige una solución general sanitizada. La confirmación verifica usuario, fundación, estado original y concurrencia antes de escribir.

La auditoría obtiene del servidor la incidencia, estado anterior, estado posterior y solución. Nunca acepta esos valores desde el navegador.

No requiere migración. Las pruebas cubren intención, datos faltantes, rol, tenant, sesión, expiración lógica, reutilización, contrato HTTP y auditoría. Para rollback, revertir este commit; las transiciones ya confirmadas se conservan como historial legítimo.
