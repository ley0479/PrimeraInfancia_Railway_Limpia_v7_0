# Control de cambio — Automatización F23.MO12.PP

**Estado:** DESARROLLO AUTORIZADO / PUBLICACIÓN PENDIENTE.

## Identificación

- ID: `CC-F23-20260930`
- Solicitud: “termina de implementar”.
- Responsable funcional: Leison Palacios.
- Revisión de partida: `49f6173ef31c8806d87f9b95f2ad81124d0b5c44` (`main`).
- Cambios locales previos: ninguno (`main...origin/main`).

## Resultado y alcance

- Objetivo: seleccionar UDS, precargar participantes desde la Base Maestra, guardar respuestas faltantes por versión y generar el consolidado F23 y las fichas disponibles.
- Componentes permitidos: servicio nuevo de caracterización F23, esquema aditivo, generador XLSM, panel dentro del Componente Psicosocial y pruebas específicas.
- Fuera de alcance: menú, Liam, autenticación, permisos generales, RPP, RAM, RAN, RRAN, Bienestarina, Nutrición y cambios al XLSM original.
- Plantilla de trabajo: copia controlada del XLSM suministrado; el original permanece intacto.

## Riesgos y controles

- Datos residuales del adjunto: limpiar solamente áreas de registro conocidas y comprobar que otra UDS no permanezca.
- Campos desconocidos: conservarlos como pendientes; nunca convertir vacíos en “No”.
- Macros/controles: preservar VBA mediante carga `keep_vba=True`; VBA no se ejecuta en el servidor.
- Más de diez convivientes: bloquear el cierre hasta disponer de una salida institucional aprobada.
- Hojas imprimibles: verificar separadamente; no declarar llenas por poblar únicamente las hojas BD.

## Pruebas requeridas

- Aislamiento por fundación y UDS; roles autorizados; precarga y faltantes.
- Versionado, guardado parcial y validación humana.
- NN/MG, documentos como texto, edad vacía, hermanos y hogares.
- Conservación de hojas, macros, áreas de impresión y ausencia de residuos.
- Regresión de menú, Liam y generadores existentes.

## Evidencia de desarrollo

- `test_caracterizacion_f23_v1.py`: `PASS` con dos participantes sintéticos y una segunda fundación aislada.
- Conservación XLSM: `PASS`; mismos componentes ZIP y componentes no editados idénticos byte a byte.
- Documento con cero inicial y captura individual: `PASS`.
- `test_centro_planeacion_psicosocial_v2_7_0.py`: `PASS`.
- `test_all_formats_continuity_v2_7_1.py`: `PASS`.
- `test_liam_action_policy_v7.py`: `PASS`.
- Motor Central de Integridad: `PASS`.
- `test_responsive_device_stability.py`: `FAIL` preexistente; la revisión de partida tampoco contiene la cadena de versión `2.3.4-responsive-stability` exigida por esa prueba. No se corrigió dentro de esta tarea.
- Prueba real en Excel de escritorio, impresión de seis páginas, dispositivo físico y PostgreSQL productivo: `NO EJECUTADO`.

## Limitaciones comprobadas

- El generador llena las hojas de registro y las celdas de captura mapeadas sin modificar los rótulos. Las hojas `V_IMPRIMIBLE_NN` y `V_IMPRIMIBLE_MG` no contienen vínculos suficientes para certificar por prueba automatizada que todos sus controles visuales reflejan las respuestas; la aceptación de impresión permanece pendiente de Excel de escritorio.
- La regla institucional para hogares con más de diez integrantes no está definida; el sistema bloquea el truncamiento.
- La clasificación inicial es NN porque la Base Maestra publicada auditada corresponde a participantes de Primera Infancia; la interfaz permite cambiar a MG mediante confirmación humana.

## Reversión

- Revertir exclusivamente el commit de este control y su implementación.
- El esquema será aditivo; no borrar tablas ni respuestas durante una reversión de código.
- Despliegue: pendiente de autorización y pruebas completas.

## Cierre de desarrollo

- Revisión implementada: commit de esta entrega; el identificador final se obtiene del historial Git tras cerrar el documento.
- Cambios fuera de alcance: ninguno identificado; las líneas del menú y los recursos de Liam no fueron modificados.
- Aceptación funcional humana: `PENDIENTE`.
- Autorización para publicar: `PENDIENTE`.
- Despliegue: `NO REALIZADO`.

## Corrección posterior al primer despliegue

- Evidencia productiva: PostgreSQL informó `UndefinedTable: relation "f23_sesiones" does not exist`.
- Causa: el runtime productivo bloquea DDL mediante `SKIP_RUNTIME_SCHEMA_DDL=1`; el esquema F23 no estaba incluido en `bootstrap_core_schema`.
- Corrección mínima: ejecutar `F23Service.init_schema()` durante el predeploy autorizado, antes de bloquear DDL.
- Hallazgo relacionado: los `JOIN` del repositorio psicosocial no declaraban el vínculo `fundacion_id` en ambas tablas y el cortafuegos multi-fundación los rechazó. Se añadieron únicamente esas igualdades de aislamiento.
- Datos existentes: no se borran ni transforman; las tablas F23 son aditivas.
