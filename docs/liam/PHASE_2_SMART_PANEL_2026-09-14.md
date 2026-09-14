# Fase 2 — Panel visual inteligente

## Cambios

- Controles accesibles para minimizar, maximizar, cerrar y alternar 40/50/60.
- Preferencia de proporción conservada en `localStorage`.
- Panel lateral en escritorio y Drawer completo en tablet/móvil.
- Se preservan tarjetas, tablas, Relación del Mes, avatar y resaltado sincronizado.

## Impacto

- Archivos modificados: controlador LIAM, CSS dinámico, índice y prueba UI.
- Migraciones, endpoints y variables: ninguno.
- Rollback: revertir el commit de esta fase.

## Pruebas

- Sintaxis JavaScript.
- Contrato de controles y estilos responsive.
- Regresión de Relación del Mes y Core del orquestador.
