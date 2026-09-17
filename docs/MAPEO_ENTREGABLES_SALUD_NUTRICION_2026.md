# Mapeo institucional de entregables de Salud y Nutrición 2026

Fuente revisada: carpeta institucional de entregables 2026, conservada fuera del repositorio.

Los archivos de la fuente son documentos diligenciados con nombres, documentos de identidad y fotografías. Se usan como evidencia funcional para diseñar la automatización, pero no se copian al repositorio ni se convierten directamente en semillas.

| Código | Destino en la plataforma | Archivo institucional de referencia | Tratamiento |
|---|---|---|---|
| E01_REGISTRO_NOVEDADES | Salud y Nutrición → Entregables → Registro de novedades | `ACTAFA_AGOSTO26_REVISION CARPETAS.docx`, `REGISTRO DE NOVEDADES_3_MARIA-EXNEIDA_CONDE_QUINTERO_AGOSTO26.docx`, `REGISTRO DE NOVEDADES-GARANTIA DE DERECHO-AGOSTO-26.docx` | Generar acta de revisión, registro individual y oficio/correo de articulación. Vincular también con el expediente del beneficiario. |
| E02_LAVADO_MANOS | Salud y Nutrición → Entregables → Lavado de manos | `ACTAFA_AGOSTO26_LAVADO DE MANOS.docx` | Acta por periodo/actividad, listado de asistencia y mínimo cuatro fotos por UCA. |
| E03_LACTANCIA | Salud y Nutrición → Entregables → Lactancia materna | `ACTAFA_AGOSTO26_CELEBRACION_LACTANCIA_MATERNA.docx`, `EVIDENCIAS_ CELEBRACION_ LACTANCIA _MATERNA_ FAMILIAS -AGOSTO26_MARINA.docx` | Acta, listado, fotos por UCA y referencia de video para remisión al ICBF. |
| E04_FICHA_LACTANCIA | Salud y Nutrición → Entregables → Ficha de lactancia | No suministrado | Requiere la plantilla institucional vacía antes de automatizar su diligenciamiento. |
| E05_ANTROPOMETRIA | Salud y Nutrición → Valoraciones y Entregables | `f6.mt1_.pp_formato_captura_de_datos_antropometricos_de_las_ninas_y_los_ninos_segunda_toma_MARINA_AGOSTO26.xlsx`, `f7.mt1_.pp_formato_de_captura_de_datos_antropometricos_de_mujeres_y_personas_en_gestacion_v1_Segunda_toma_MarinaAGOSTO26.xlsx` | Dos salidas oficiales: niñas/niños y mujeres/personas gestantes. Alimentar desde Base Maestra y valoraciones validadas. |
| E06_SIGNOS_FISICOS | Salud y Nutrición → Entregables → Signos físicos | `f1.go4_.mt1_.pp_F.I_de_signos_fisicos__a_la_desnutricion_aguda_v1_2 -MARINA_AGOSTO26.xlsx` | Conservar estructura Excel oficial y generar por tenant, periodo y UCA. |
| E07_MONITOREO_DNT | Salud y Nutrición → Alertas/seguimiento y Entregables | No suministrado | Requiere formato oficial de monitoreo semanal DNT/riesgo antes de automatizar la salida. |
| E08_CONCERTACION_MINUTA | Salud y Nutrición → Entregables → Concertación de minuta | Acta institucional de concertación de minuta | Generar por comunidad/UCA, minuta y grupo etario; anexar listado y fotos. |
| E09_CONTROL_CALIDAD | Salud y Nutrición → Entregables → Control de calidad | `ACTA_AGOSTO26_CONTROL_CALIDAD.docx` | Acta de verificación de alimentos, almacenamiento, vencimientos y evidencias. |
| E10_LIMPIEZA_DESINFECCION | Salud y Nutrición → Entregables → Limpieza y desinfección | `ACTA_AGOSTO_26_LIMPIEZA Y DESINFECCION.docx` | Acta y fotografías por UCA; anexar muestras de saneamiento básico. |
| E11_ENCUENTROS_HOGAR | Salud y Nutrición → Expediente integral y Entregables | `ENCUENTRO EN EL HOGAR_ELBIMAR_AGOSTO26.docx` | Documento individual asociado al beneficiario; consolidar muestras en el informe mensual. |
| E12_ARTICULACION_INTERINSTITUCIONAL | Salud y Nutrición → Rutas/alertas y Entregables | No suministrado como archivo independiente | Generar oficio desde una novedad validada, destinatario y entidad de salud confirmados. |
| E13_ENTREGA_RPP | Salud y Nutrición → Entregables → Entrega RPP | `EVIDENCIAS ENTREGA RPP AGOSTO26.docx` | Registro fotográfico agrupado por UCA, fecha y actividad. |
| E14_OLLAS_REFRIGERIOS | Salud y Nutrición → Entregables → Ollas/refrigerios | `EVIDENCIAS PREPARACION OLLA COMUNITARIA -AGOSTO26.docx` | Registro fotográfico por UCA que evidencie preparación y participación familiar. |
| E15_CUALIFICACION_TH | Salud y Nutrición → Entregables → Cualificación del talento humano | `ACTA_AGOSTO26_TALENTO HUMANO.docx` | Acta, listado y fotos; temas parametrizados por periodo. |

## Documento rector

`ENTREGABLES MES AGOSTO PAZCIFICO VIVE  1).docx` funciona como matriz de requisitos del periodo. Debe importarse como programación mensual, no como evidencia de un entregable individual.

## Reglas institucionales identificadas

- Las evidencias deben nombrarse con actividad, fecha y UCA.
- Cada acta debe contener evidencias de cada UCA incluida.
- Se requieren como mínimo cuatro fotografías por entregable y por UCA.
- Los documentos individuales deben permanecer vinculados al expediente del beneficiario y al tenant correspondiente.
- Ningún texto planeado puede registrarse como hecho ejecutado sin confirmación humana.
- Las plantillas faltantes permanecen bloqueadas; no se debe fabricar una versión supuestamente oficial.

## Flujo automatizado implementado

1. En **Salud y Nutrición → Entregables**, seleccionar mes, año y UCA y crear los 15 entregables.
2. Usar **Registrar actividad** en el entregable correspondiente.
3. Guardar como borrador mientras la información no esté verificada.
4. Confirmar la actividad solamente después de diligenciar fecha, responsable, objetivo y desarrollo real.
5. Cargar las fotografías y soportes; la plataforma los renombra por actividad, fecha y UCA.
6. Generar acta, listado, oficio o formato según los requisitos del entregable.
7. Validar el entregable. La validación comprueba actividad confirmada, archivos y cantidad mínima de fotos.
8. Generar el informe Word o preparar el periodo en **Informe mensual automatizado**. Los temas e indicadores se alimentan desde las actividades confirmadas.
9. Coordinación aprueba el periodo; después de la aprobación queda bloqueado y sellado para auditoría.
10. Descargar informe, matriz y ZIP final.

Las actividades guardadas como borrador no aparecen como ejecutadas en actas ni informes. Los archivos y registros se almacenan de forma separada por fundación.
