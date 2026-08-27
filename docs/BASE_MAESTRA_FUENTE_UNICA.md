# Base Maestra como fuente institucional única

## Regla obligatoria

Cuando una fundación tiene una versión publicada, los participantes, unidades,
Talento Humano, coordinadores y datos consolidados de salud se consultan desde
las tablas `master_*`. Las tablas `beneficiarios` y `usuarios` quedan únicamente
como compatibilidad para instalaciones que todavía no han publicado su primera
Base Maestra.

Los módulos operativos conservan sus datos propios: actividades, planeaciones,
evidencias, valoraciones, seguimientos, aprobaciones e históricos. Publicar una
nueva Base Maestra no elimina ni sobrescribe esos movimientos.

## Modalidades de alimentación

- Lectura directa obligatoria: participantes, unidades, Salud y Nutrición,
  Psicosocial/Familias, Planeación, formatos y reportes.
- Proyección controlada: Talento Humano, coordinadores, docentes, equipos y
  asignaciones. Se reconstruye desde `master_talento_humano` al publicar.
- Información operativa: permanece en las tablas propias de cada módulo y se
  relaciona por tenant, documento y unidad.

Cada publicación registra su estado en `master_projection_status`. Así se puede
distinguir una lectura directa disponible de un error real de propagación.

## Protección histórica

Las referencias antiguas de Psicosocial y Familias no se eliminan. Cuando el
documento existe en la versión publicada, la plataforma presenta el registro
maestro vigente. Si ya existe una versión publicada y el documento antiguo no
aparece en ella, el sistema no expone el registro heredado como participante
activo.
