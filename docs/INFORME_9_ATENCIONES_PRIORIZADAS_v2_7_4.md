# Informe Mensual de las 9 Atenciones Priorizadas

## Alcance implementado

Módulo aditivo dentro de Reportes Gerenciales. Consolida información existente,
permite completar indicadores semiautomáticos, registra evidencias, valida el
cierre y genera PowerPoint, PDF, Excel y ZIP.

## Fuentes

- Base Maestra / Cuéntame: cobertura, unidades, documentos y grupos RPP.
- Talento Humano: personal activo y cargos.
- Salud y Nutrición: valoraciones, alertas y diagnósticos.
- Calendario/entregables: formación a familias y actividades detectadas.
- Captura confirmada: materiales, carné, afiliación, vacunación y evidencias.

## Reglas

- Los cálculos son determinísticos; no los produce IA.
- Un informe con errores o atenciones incompletas no puede aprobarse.
- Al aprobar se genera un snapshot JSON con SHA-256.
- Un informe aprobado no admite cambios.
- Todas las consultas y mutaciones se acotan por `fundacion_id` obtenido de la sesión.
- La presentación descrita se considera referencia interna configurable hasta que
  se confirme una plantilla y fórmulas oficiales del ICBF.

## API

- `GET /api/reportes-gerenciales/9-atenciones/catalogo`
- `GET /api/reportes-gerenciales/9-atenciones/consolidar`
- `POST /api/reportes-gerenciales/9-atenciones/informes`
- `GET /api/reportes-gerenciales/9-atenciones/informes/{id}`
- `PUT /api/reportes-gerenciales/9-atenciones/informes/{id}/atenciones/{codigo}`
- `POST /api/reportes-gerenciales/9-atenciones/informes/{id}/atenciones/{codigo}/evidencias`
- `POST /api/reportes-gerenciales/9-atenciones/informes/{id}/aprobar`
- `POST /api/reportes-gerenciales/9-atenciones/informes/{id}/generar`
- `GET /api/reportes-gerenciales/9-atenciones/informes/{id}/descargar/{pptx|pdf|xlsx|zip}`

## Rollback

Revertir el commit del módulo retira interfaz y rutas. Las tablas `rg9_*` son
aditivas y pueden conservarse sin afectar otros módulos. No deben borrarse en
producción para preservar informes y snapshots aprobados.
