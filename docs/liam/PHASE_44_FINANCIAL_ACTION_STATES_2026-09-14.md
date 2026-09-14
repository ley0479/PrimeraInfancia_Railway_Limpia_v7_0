# Fase 44 · Estados confiables de acciones financieras

Las propuestas confirmables de créditos y licencias enlazan ahora su auditoría mediante el `proposal_id` generado por el servidor. La acción, fundación objetivo y estados anterior/posterior se leen exclusivamente de `lia_action_proposals`; el navegador no puede suministrarlos.

Solo se conservan los campos funcionales permitidos: estado, vencimiento, créditos disponibles y créditos incluidos. Cualquier secreto u otro campo queda excluido por lista blanca.

No requiere otra migración. Se verifican enlace, resultado, estados confiables y filtrado de campos. Para rollback, revertir este commit sin eliminar el historial ya creado.
