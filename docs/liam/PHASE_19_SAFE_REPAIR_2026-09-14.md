# Fase 19: autorreparación controlada

## Resultado

Liam reutiliza el Motor de Integridad existente mediante un registro cerrado. Puede iniciar un plan sin cambios y proponer su aplicación, pero esta exige confirmación visible y rol `SUPERADMIN`.

## Garantías

- No existe entrada para comandos de shell, SQL o código arbitrario.
- El cliente verifica el registro autorizado antes de invocar el motor.
- La aplicación conserva confirmación explícita de riesgo crítico.
- La operación real sigue protegida por el endpoint de Integridad y se ejecuta como trabajo auditable.
- No se modifican reglas ni datos de negocio.

## Archivos

- Nuevos: `repair_registry.py`, su prueba y este documento.
- Modificados: política, intenciones, rutas, controlador, prueba de intenciones e `index.html`.

## Migraciones

No requiere migraciones ni variables nuevas.

## Pruebas y rollback

Se verifican registro cerrado, roles, intenciones, confirmación, regresión HTTP, JavaScript y diff. Para revertir, aplicar `git revert` al commit de esta fase; el Motor de Integridad original permanece intacto.
