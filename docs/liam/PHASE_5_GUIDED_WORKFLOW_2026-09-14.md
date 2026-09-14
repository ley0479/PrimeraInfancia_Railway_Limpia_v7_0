# Fase 5 — Recorridos “Hazlo conmigo” con progreso

## Cambios realizados

- Los recorridos existentes guardan el paso activo en `sessionStorage`.
- Al reabrir un recorrido dentro de la misma sesión, Liam continúa desde el último paso.
- Un recorrido puede reiniciarse explícitamente con la opción `restart`.
- Los pasos que esperan una acción real ya no pueden adelantarse manualmente.
- El evento funcional esperado habilita el avance; Liam no pulsa botones ni ejecuta la acción por el usuario.
- Completar el recorrido elimina el progreso; cancelarlo lo conserva para continuar después.

## Archivos modificados

- `frontend/js/liam/liam-tour-engine.js`
- `frontend/js/liam/liam-controller.js`
- `frontend/index.html`

## Archivo nuevo

- `backend/tests/test_liam_guided_progress_v7.py`

## Migraciones y variables

No se requieren. El progreso es temporal y permanece solamente en la sesión del navegador.

## Pruebas realizadas

- Contrato de persistencia, reanudación y reinicio.
- Bloqueo de avance en pasos obligatorios.
- Avance mediante eventos reales de negocio.
- Regresión de recorridos prioritarios, Talento Humano, Nutrición, Administración y componentes técnicos.

Resultado: todas las pruebas ejecutadas finalizaron correctamente.

## Riesgos y pendientes

- El progreso no se sincroniza entre dispositivos, coherente con la memoria temporal de sesión.
- Cada flujo adicional deberá declarar sus eventos funcionales cuando un paso sea obligatorio.

## Rollback

Revertir el commit independiente de esta fase. No existe información persistente en servidor que restaurar.
