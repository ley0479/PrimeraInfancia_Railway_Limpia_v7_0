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
- El año de una referencia normativa no se transforma en fecha operativa y su vigencia no se certifica.
- La revisión usa un número de revisión; un editor desactualizado recibe conflicto HTTP 409.

### Uso reproducible de Fase 1

1. Cargar JPG, PNG o PDF en Motor Documental y completar/reintentar su extracción.
2. Abrir Salud y Nutrición → **Temáticas, actividades e informes**.
3. Indicar el ID del documento y, opcionalmente, el periodo; ejecutar **Extraer para revisión**.
4. Comparar con **Ver original**, corregir las denominaciones propuestas y seleccionar periodo/unidades.
5. Publicar con la confirmación explícita. El mensaje confirma que no se registró ejecución.

### Límites y bloqueos

- El afiche real del usuario no está disponible en el entorno: el escenario visual A permanece **NO VERIFICADO**. El test incluido usa un fixture textual y lo declara expresamente.
- `pytest` no está instalado en el Python local. El test nuevo es ejecutable directamente con Python; la regresión completa debe correrse en el entorno de CI/dependencias.
- La autorización actual es por rol y tenant. La restricción adicional por unidades asignadas al usuario requiere definir/reutilizar el catálogo institucional correspondiente en Fase 2.
- Aún no se implementaron planeación, calendario, ejecución, informes ni acciones de Liam dentro de este flujo.

### Rollback

Revertir los archivos de esta entrega desactiva rutas e interfaz. Las tablas `sn_*tematicas*` pueden conservarse sin afectar rutas históricas; no deben borrarse automáticamente si ya contienen publicaciones.
