# Manual Maestro de Usuario y conocimiento de LIAM

La fuente publicable está en `knowledge/liam/`. No se debe editar el PDF como documento independiente: la plataforma lo genera desde los mismos archivos JSON que consulta LIAM.

## Componentes

- `index.json`: versión, estado y lista de fuentes.
- `platform_identity.json`: propósito, alcance y seguridad.
- `modules/`: fichas de módulos y controles.
- `roles/`: enfoque permitido por rol.
- `workflows/`: guías rápidas.
- `errors/`: errores estructurados, comprobaciones y acciones.

Cada ficha funcional debe conservar `app_version`, `guide_version`, `last_verified_at` y `status`. Los estados permitidos para publicación son `draft`, `review`, `verified`, `published` y `outdated`.

## Regla de mantenimiento

Todo cambio funcional debe actualizar código, ficha, recorrido o `data-help-id` afectado y pruebas en el mismo cambio. Los identificadores son estables; cambiar el texto visible de un botón no obliga a cambiar su `help_id`.

## Primera cobertura verificada

La versión piloto cubre Panel Principal, Base Maestra, Calendario, Formatos/RPP, Motor Documental y Administración; contiene guías por rol y un catálogo inicial de errores RPP, tablero, permisos, tenant y archivos. El contenido se filtra en el backend con el rol autenticado antes de enviarse al navegador o al PDF.

## Ampliación

Para agregar un módulo:

1. Registre su ficha y roles en `knowledge/liam/modules/`.
2. Agregue `data-help-id`, `data-help-module` y `data-help-screen` al control real.
3. Registre el flujo o error relacionado.
4. Ejecute `backend/tests/test_liam_manual_master_v7.py`.
5. Marque la ficha como `verified` solamente después de probarla con cada rol autorizado.
