# Salud y Nutrición — temáticas, actividades e informes

## Estado de la entrega

Fase 0 auditada y Fase 1 iniciada de forma aditiva. No se realizó despliegue productivo.

### Mapa de reutilización

| Necesidad | Componente reutilizado | Ampliación |
|---|---|---|
| Original privado, hash, lectura y OCR | Motor Documental IDP | Vínculo `idp_documento_id` y contrato temático 1.0 |
| Unidades y responsables | Base Maestra | Resolución de `master_unidades` dentro del tenant |
| Actividades, asistencia y productos | Salud Integral | Relación muchos-a-muchos `sn_actividad_temas` |
| Plantillas, versiones y descargas | Centro Documental | Pendiente para Fase 3 |
| Fechas operativas | Calendario Inteligente | Pendiente para Fase 2; publicar no crea eventos |
| Operación conversacional | Registro y política de Liam | Pendiente para Fase 4 |

### Contrato y reglas implementadas

- Estados separados: extracción pendiente de revisión y publicación.
- El título original es `EXTRAIDO`; normalización y categoría son `PROPUESTO_IA`; las correcciones quedan como `EDITADO_USUARIO`.
- La lectura original se conserva en `resultado_original_json`; cada corrección conserva antes/después y actor.
- Publicar exige periodo `AAAA-MM`, al menos una unidad activa de Base Maestra y confirmación explícita.
- La publicación es idempotente por tema, versión, periodo y unidad. No crea actividad, fecha, asistencia, evidencia, resultado ni aprobación de informe.
- Una planeación confirmada reutiliza Salud Integral, admite varios temas por actividad y no agrega participantes. Sin día queda `SIN_PROGRAMAR`; con fecha crea un único enlace idempotente al Calendario.
- El año de una referencia normativa no se transforma en fecha operativa y su vigencia no se certifica.
- La revisión usa un número de revisión; un editor desactualizado recibe conflicto HTTP 409.

### Uso reproducible de Fase 1

1. Abrir Salud y Nutrición → **Temáticas, actividades e informes**.
2. Cargar directamente un JPG, PNG o PDF; la interfaz reutiliza Motor Documental, conserva el original privado y solicita OCR solo cuando hace falta. También puede indicarse el ID de un documento previamente cargado.
3. Confirmar el periodo y ejecutar la extracción para revisión.
4. Comparar con **Ver original**, corregir las denominaciones propuestas y seleccionar periodo/unidades.
5. Publicar con la confirmación explícita. El mensaje confirma que no se registró ejecución.

### Límites y bloqueos

- El afiche real del usuario no está disponible en el entorno: el escenario visual A permanece **NO VERIFICADO**. El test incluido usa un fixture textual y lo declara expresamente.
- `pytest` no está instalado en el Python local. El test nuevo es ejecutable directamente con Python; la regresión completa debe correrse en el entorno de CI/dependencias.
- La consulta y publicación filtran también las unidades asignadas al usuario; coordinación conserva su alcance institucional configurado.
- Aún no se implementaron planeación, calendario, ejecución, informes ni acciones de Liam dentro de este flujo.

### Rollback

Revertir los archivos de esta entrega desactiva rutas e interfaz. Las tablas `sn_*tematicas*` pueden conservarse sin afectar rutas históricas; no deben borrarse automáticamente si ya contienen publicaciones.
