# Fase 40 · Base de Conocimiento de incidencias

## Resultado

LIAM puede consultar una solución conocida mediante un código de error exacto. La búsqueda combina el catálogo interno confirmado con el historial sanitizado de incidencias de la fundación activa.

## Seguridad y alcance

- Herramienta cerrada `get_known_solution`; no acepta SQL.
- Toda incidencia se filtra por `fundacion_id` de la sesión autenticada.
- No devuelve mensajes técnicos, trazas, contexto ni causas libres almacenadas.
- Los códigos no catalogados usan una causa prudente y la recomendación sanitizada más reciente.
- Es una operación de solo lectura disponible para roles autenticados.

## Interfaz

Las respuestas incluyen tarjeta enriquecida con ocurrencias, resueltas, estado reciente, causa orientativa y solución. El mismo contenido alimenta texto y voz.

## Pruebas

- Código conocido por catálogo aun sin incidentes locales.
- Conteo y resueltos dentro de una sola fundación.
- Exclusión de incidencias de otra fundación con el mismo código.
- Ausencia de mensajes técnicos, secretos, trazas y causas libres.
- Rechazo de códigos desconocidos sin evidencia local.

## Migraciones

No requiere migración: reutiliza `lia_error_incidents`.

## Rollback

Revertir el commit de esta fase elimina la herramienta, intención y presentación sin modificar datos existentes.
