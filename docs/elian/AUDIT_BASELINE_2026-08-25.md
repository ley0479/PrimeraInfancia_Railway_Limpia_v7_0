# Auditoría inicial de la ampliación ELIAN

Fecha del baseline: 2026-08-25. Commit inicial: `6981c016a4004603382ffe6d6d0d38d8a0192520`.

## Arquitectura encontrada

- Flask registra el asistente mediante el módulo aditivo `asistente_capacitacion` y el prefijo `/api/asistente-capacitacion`.
- La autorización efectiva proviene de la sesión del backend y de `ROLE_MENU_PERMISSIONS`.
- La interfaz es una aplicación HTML/JavaScript con navegación interna mediante `mostrarSeccion` y hash registrado.
- Existían registros cerrados de controles, anclajes y 16 recorridos locales de LIAM.
- Existían preferencias por usuario y progreso simple por módulo en tablas `lia_*` y `ayuda_progreso_usuario`.
- La presentación anterior enumeraba módulos dentro del panel, pero no navegaba entre ellos ni esperaba su carga.

## Brechas confirmadas antes del cambio

- Sin recorrido transversal versionado.
- Sin eventos `elian:module-*` para gobernar la continuidad.
- Sin pausa, reanudación, repetición y salto persistentes del recorrido completo.
- Sin registro lógico central de módulos con los ocho aspectos obligatorios.
- Sin configuración visual global por fundación.
- Recurso visual LIAM provisional y no identificado como ELIAN afrocolombiano institucional.

## Decisión de compatibilidad

Se conserva el prefijo API y las tablas `lia_*` existentes para no romper integraciones. ELIAN es la identidad funcional visible; la ampliación usa tablas `elian_*` aditivas y puede desactivarse sin alterar módulos operativos.

## Riesgos y pendientes del baseline

- Las variantes tecnológica, educativa y femeninas necesitan recursos gráficos profesionales propios.
- Los controles internos de algunos módulos del registro todavía no tienen anclajes visuales específicos.
- El recorrido debe verificarse en navegador real con cada rol y con datos de prueba de dos fundaciones.

