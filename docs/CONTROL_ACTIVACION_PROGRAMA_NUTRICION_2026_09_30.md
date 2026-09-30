# Control de activación — Programa de Nutrición ICBF

## Autorización y alcance

- Autorización humana: el responsable solicitó expresamente “actívalo”.
- Revisión de partida: `d2c4582`.
- Objetivo: habilitar en producción la integración multiprograma ya publicada dentro de Salud y Nutrición.
- Permitido: incorporar copias verificadas de RFPP/F2, configurar sus rutas y habilitar las banderas del módulo.
- Excluido: modificar menú, Liam, autenticación, permisos, Base Maestra, calendario, formatos originales o datos existentes.

## Plantillas verificadas

- RFPP: `backend/seed_data/templates_originales/oficiales_icbf/rfpp_servicio_integrado_v2026.xlsx`.
  SHA-256: `ED437C0D07B33A0D86C8F344BB752775C334EAB511A2E47D04F1BE8E5844B5BC`.
- F2: `backend/seed_data/templates_originales/oficiales_icbf/f2_bienestarina_servicio_integrado_v2026.xlsx`.
  SHA-256: `FC6A20E85F211F06EF6466EE8267CC9B264EFA75FD64E5689CB4D60FF21173AD`.

Los archivos suministrados en Descargas no se modifican. Las copias versionadas son fuentes de solo lectura para generar nuevos libros.

## Configuración prevista

- `ICBF_RFPP_TEMPLATE_PATH=/app/backend/seed_data/templates_originales/oficiales_icbf/rfpp_servicio_integrado_v2026.xlsx`
- `ICBF_F2_TEMPLATE_PATH=/app/backend/seed_data/templates_originales/oficiales_icbf/f2_bienestarina_servicio_integrado_v2026.xlsx`
- `ENABLE_ICBF_MULTIPROGRAM=true`
- `ENABLE_ICBF_MULTIPROGRAM_PRODUCTION=true`

## Pruebas y reversión

- Generación y preservación RFPP/F2 sobre las copias desplegables: `PASS`.
- Fases multiprograma 1–4: `PASS`.
- Intenciones y política de acciones Liam: `PASS`.
- Prueba visual contextual previa en diez viewports: `PASS`; no se modificó UI en esta activación.
- `git diff --check`: `PASS`.
- Verificación productiva autenticada: pendiente.
- Reversión funcional: establecer ambas banderas `ENABLE_ICBF_MULTIPROGRAM*` en `false`. Esto no borra datos ni requiere restaurar la plataforma.
