# LÍA — Línea Inteligente de Ayuda

## Alcance

Capa transversal multimodal de solo orientación. Detecta el rol autenticado y
el módulo visible, responde por escrito, admite dictado cuando el navegador lo
permite, muestra requisitos y pasos curados, señala el acceso del módulo,
consulta pendientes y ofrece lectura en voz alta. Nunca modifica registros
misionales ni confirma acciones en nombre del usuario.

## Arquitectura

- `guides.py`: conocimiento contextual curado y versionable.
- `GET /api/asistente-capacitacion/contexto`: guía filtrada con el mapa real de
  menús del rol en backend.
- `POST /api/asistente-capacitacion/progreso`: guarda únicamente avance del
  recorrido por fundación, usuario y módulo.
- `asistente-capacitacion.js`: widget, recorrido, voz y sugerencia local por
  inactividad. No transmite pulsaciones, formularios ni tiempo de actividad.
- `speechSynthesis`: voz local del navegador, sin servicio externo.

El asistente documental `/api/asistente-icbf` continúa separado como búsqueda
en fuentes institucionales. El asistente contextual no inventa reglas ni usa un
modelo generativo por defecto.

## Privacidad y control

- No registra contraseñas, tokens, cuerpos de formularios o datos personales.
- No ejecuta acciones en nombre del usuario.
- El recorrido se puede omitir, repetir y cerrar.
- La sugerencia por inactividad aparece una vez por módulo y sesión.
- Los módulos no autorizados se rechazan en backend.

## Verificación

- Sintaxis Python y JavaScript: PASS.
- Auditoría PostgreSQL: PASS; 1.617 SQL, cero incompatibilidades.
- Login, contexto, progreso y frontend: HTTP 200.
