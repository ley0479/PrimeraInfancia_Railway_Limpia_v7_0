# Reporte de implementación de LÍA

## Resumen

Se implementó LÍA como módulo independiente y reversible: avatar humano,
asistencia escrita institucional, presentación por rol, guías para el menú real,
recorridos, voz encadenada opcional, herramientas de lectura, auditoría,
preferencias, feedback, privacidad y rate limit.

## Seguridad

El tenant y rol provienen de la sesión. Las herramientas son una lista cerrada,
no existe SQL/JavaScript/URL arbitraria y no hay herramientas de escritura. IA,
voz y Realtime permanecen apagados. Las preguntas no se guardan en auditoría.

## Datos

Tablas aditivas: `ayuda_progreso_usuario`, `lia_audit_events`,
`lia_user_preferences` y `lia_feedback`, todas vinculadas a fundación y usuario.
Rollback funcional: apagar la bandera maestra; no borrar tablas.

## Endpoints

`config`, `contexto`, `presentation`, `chat`, `progreso`, `health`, `tools`,
`preferences` y `feedback`, dentro de `/api/asistente-capacitacion`.

## Verificación

Pasaron pruebas de LÍA, Base Maestra, calendario, evidencias, motor documental,
plantillas, formatos, RPP, relación mensual, multi-tenant y responsive. Consulte
`TESTING.md` para el inventario.

## Pendientes externos reales

- Confirmar autor y fecha institucional de la plataforma.
- Sustituir el PNG provisional de fondo oscuro por Rive o PNG transparente.
- Configurar y validar proveedor externo con documentación oficial accesible.
- Ejecutar piloto antes de voz y mantener Realtime para una fase posterior.
