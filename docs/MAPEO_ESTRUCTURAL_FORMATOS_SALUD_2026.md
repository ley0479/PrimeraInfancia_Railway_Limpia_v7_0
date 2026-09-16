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

## Plantilla limpia localizada

Se localizó `Desktop/2026/formato para suvir/FORMATO ACTA DE GRUPAL 2026.docx`. La inspección encontró una tabla principal 12×5, dos bloques fotográficos 2×2, cero imágenes diligenciadas y los siguientes doce campos reconocibles: fecha, hora inicial, hora final, lugar, unidad, responsable, tema, objetivo, agenda, desarrollo, compromisos y responsables de compromisos.

El Motor Documental detecta ahora esos campos sin persistir texto libre y propone coordenadas de celda en estado `REQUIERE_REVISION`. Solamente un mapeo marcado `APROBADO` o `CONFIRMADO` puede escribir valores. La prueba con datos sintéticos verificó los doce campos por separado y una copia combinada conservando el original intacto. La comparación visual de paginación continúa pendiente.

## Pendientes verificables

- Registrar y aprobar en la fundación la plantilla limpia localizada; encontrarla en disco no equivale a aprobarla en la plataforma.
- Confirmar el mapeo propuesto y ampliar los campos que no existen explícitamente en el acta grupal, como dificultades y resultados reportados.
- Ejecutar comparación visual de páginas contra el formato oficial.
- El afiche del caso de aceptación no está presente como JPG, PNG, PDF o PPTX dentro de la carpeta inspeccionada; su lectura visual real sigue pendiente.
