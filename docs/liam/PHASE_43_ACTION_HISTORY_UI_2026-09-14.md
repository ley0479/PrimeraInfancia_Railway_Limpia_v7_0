# Fase 43 · Historial administrativo de acciones LIAM

Administración incorpora una tarjeta de historial de acciones. El endpoint paginado `/api/asistente-capacitacion/actions/history` exige la bandera administrativa y rol Gerencia o SUPERADMIN, y filtra siempre por la fundación activa.

La tabla muestra fecha, usuario, acción, riesgo y resultado. Se construye con nodos DOM y `textContent`, sin HTML proveniente de datos. El contrato no entrega estados internos, argumentos, errores ni detalles técnicos.

No requiere una migración adicional a la fase 42. Las pruebas cubren permisos, tenant, paginación, contrato HTTP, render seguro y actualización de caché. Para rollback, revertir este commit.
