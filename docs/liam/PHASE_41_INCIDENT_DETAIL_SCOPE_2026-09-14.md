# Fase 41 · Alcance seguro del detalle de incidencias

El detalle de una incidencia ahora aplica simultáneamente el tenant y el rol de la sesión. Los roles operativos solo consultan incidentes propios; Gerencia y SUPERADMIN pueden consultar los de su fundación activa.

La respuesta excluye mensaje técnico, `request_id` y contexto interno. Conserva únicamente el diagnóstico funcional sanitizado necesario para orientar al usuario.

No requiere migración. Se verificaron propiedad, aislamiento entre fundaciones y ausencia de columnas técnicas. Para rollback, revertir el commit independiente de esta fase.
