# Mapeo estructural de formatos de Salud y Nutrición 2026

Fecha de inspección: 2026-09-16. Fuente autorizada por el usuario: carpeta `ENTREGABLES MARINA`.

La inspección fue de solo lectura y registró únicamente estructura (tablas, secciones e imágenes). No se copiaron textos diligenciados, nombres, identificaciones, fotografías ni archivos al repositorio.

## Familias detectadas

| Familia | Estructura observada | Uso permitido |
|---|---|---|
| Acta institucional | Tabla principal 14×5, orientación vertical, anexos fotográficos en tablas 2×2 | Referencia para localizar una plantilla limpia; no usar los documentos diligenciados como plantilla |
| Acta de concertación de minuta | Tabla 9×2, bloques 1×1, tabla 12×3, secciones vertical y horizontal | Flujo documental independiente |
| Encuentro en el hogar | Tablas 6×4, 6×2, 5×1 y anexos | Flujo pedagógico independiente |
| Relación mensual de entregables | Tabla 18×4 | Lista de chequeo/entregables existente |
| Evidencias | Series de tablas 2×2 con imágenes | Anexos auténticos asociados a una actividad; nunca generados automáticamente |
| Registros de novedades | Tablas 6×2 y 20/22×7 | Flujo de garantía de derechos, fuera del informe temático |
| Formatos antropométricos | Libros con hojas de instrucciones, captura y hojas por unidad | Mantener en el flujo CAPTURE/Base Maestra; no convertirlos en informes narrativos |

## Decisión de integración

El Centro Documental existente es el registro canónico de plantillas. La plantilla limpia del informe debe cargarse con código y tipo `INFORME_SALUD_NUTRICION`, revisar su mapeo y aprobarse explícitamente. Un acta ya diligenciada no es una plantilla aprobable porque podría conservar datos personales y evidencias previas.

Mientras no exista una plantilla limpia aprobada y un mapeo confirmado, el módulo puede producir únicamente un borrador interno trazable. La API informa de forma explícita `FORMATO_INTERNO`; no lo declara institucional.

## Pendientes verificables

- Recibir o localizar la plantilla limpia oficial de informe/acta de Salud y Nutrición.
- Definir y aprobar los marcadores de campos sobre una copia: unidad, periodo, actividad, fecha real, responsable, temáticas, metodología, resultados reportados, dificultades, compromisos, asistencia y anexos.
- Ejecutar comparación visual de páginas contra el formato oficial.
- El afiche del caso de aceptación no está presente como JPG, PNG, PDF o PPTX dentro de la carpeta inspeccionada; su lectura visual real sigue pendiente.
