# Fase 23: tablero conversacional por rol

## Resultado

Liam responde “mi tablero”, “mi resumen del día”, “cómo voy hoy” y “qué tengo para hoy” consolidando tareas, entregables y alertas. Presenta KPIs y prioridades distintas para docente, coordinador, gerente y superadministrador.

## Permisos y aislamiento

- Cada fuente aplica la fundación autenticada.
- Docentes reciben tareas y registros propios.
- El alcance de equipo solo se acepta para coordinación, gerencia o superadministración.
- Una fuente no disponible degrada su bloque sin inventar ceros como datos confirmados ni tumbar el tablero.
- El tablero es exclusivamente de lectura.

## Archivos, pruebas y rollback

Se amplían catálogo, política, intenciones, orquestación, contrato visual, voz y pruebas. No hay migraciones. Se verifican aislamiento entre tenants, rol, degradación parcial y regresiones. Para rollback, revertir el commit independiente de esta fase.
