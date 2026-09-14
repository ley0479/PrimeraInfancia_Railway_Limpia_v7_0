# Fase 33: cierre de la compuerta de acciones

## Resultado

`LIAM_ACTIONS_ENABLED=false` bloquea ahora tanto herramientas y confirmaciones servidor como propuestas destinadas a ejecución en el navegador. La decisión usa el nivel de riesgo registrado en la política central:

- generación;
- modificación;
- crítico;
- administración;
- financiero.

Las consultas, la navegación y la orientación permanecen disponibles. La respuesta indica que las acciones están apagadas y no devuelve `action_proposal`, por lo que una interfaz no puede mostrar una confirmación ejecutable residual.

## Pruebas y rollback

La prueba HTTP solicita un RPP completo con acciones apagadas y verifica respuesta segura, ausencia de propuesta y ausencia de confirmación. También se conservan las pruebas del catálogo, herramientas y fallback visual. No hay migraciones. Para rollback, revertir el commit independiente de esta fase.
