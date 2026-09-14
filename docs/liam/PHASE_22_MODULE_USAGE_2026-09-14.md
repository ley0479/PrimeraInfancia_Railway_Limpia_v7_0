# Fase 22: analítica de uso de módulos

## Resultado

Liam clasifica los módulos de la fundación activa como frecuentes, de uso moderado, poco usados o sin actividad durante un periodo de 1 a 365 días. El Centro Liam incorpora el total sin actividad.

## Seguridad

- Fuente: auditoría funcional persistida.
- Filtro obligatorio por fundación autenticada.
- Acceso para `SUPERADMIN` y `GERENTE` dentro de su alcance.
- No elimina, oculta ni desactiva módulos.
- No interpreta ausencia de eventos como abandono definitivo.

## Archivos, pruebas y rollback

Se amplían catálogo, política, intenciones, herramienta, Centro Liam, tarjeta visual, voz y pruebas. No hay migraciones. Se prueban aislamiento entre fundaciones, roles, clasificaciones y regresiones. Para rollback, revertir el commit independiente de esta fase.
