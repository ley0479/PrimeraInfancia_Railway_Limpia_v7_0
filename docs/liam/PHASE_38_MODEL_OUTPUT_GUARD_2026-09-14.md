# Fase 38: guardián de salida generativa

## Resultado

La respuesta opcional del modelo pasa ahora por una validación determinista antes de reemplazar el borrador institucional.

Se rechazan:

- afirmaciones en primera persona de ejecución, publicación, eliminación, modificación, envío, despliegue, restauración o cambios administrativos no confirmados;
- conteos de niños, beneficiarios, UDS, coordinadores, docentes o fundaciones cuando la respuesta base no tiene confianza confirmada.

Cuando se rechaza una salida, el usuario recibe el borrador institucional y el proveedor se identifica como `institutional_guarded`. El resultado incluye la razón del guardián para observabilidad.

## Límites

El guardián complementa el prompt y Permission Gateway; no reemplaza herramientas ni validación de datos. Las explicaciones procedimentales seguras continúan permitidas.

## Pruebas y rollback

Las pruebas simulan un proveedor que afirma haber eliminado usuarios y verifican el fallback, sin llamadas de red. No hay migraciones. Para rollback, revertir el commit independiente de esta fase.
