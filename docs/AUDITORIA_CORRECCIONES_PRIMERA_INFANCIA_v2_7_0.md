# Auditoría y correcciones — Primera Infancia v2.7.0

**Entrega:** `PrimeraInfancia_v2_7_0_AUDITADA_CORREGIDA`  
**Fecha UTC:** 2026-08-16T22:40:10+00:00  
**Fuente auditada:** `02699eff-84ff-4f39-a51d-80eefa4f5fa3.rar`  
**SHA-256 de la fuente:** `a6b2c4b1713a56ae7bc51813b1390c1717ece5ce7d8859bb5dfc0f4a9058bab5`

## 1. Alcance

La auditoría se hizo sobre el RAR exacto suministrado por el usuario. Se revisaron y corrigieron las fallas de arranque PostgreSQL/Railway, la ejecución de DDL durante runtime, la introspección global de esquema, transacciones abortadas, lanzadores Windows, el expediente UCA/Talento Humano, el calendario inteligente, el lector de listas de chequeo y la generación del formato oficial RAM/listado de asistencia.

## 2. Causas raíz encontradas

1. `dbapi_compat.py` consultaba **todas** las columnas del esquema `public` para responder a `PRAGMA table_info(tabla)`. En Railway esa consulta alcanzaba `statement_timeout` al registrar Gestión Pedagógica, Gestión por Coordinador y Planeación Pedagógica.
2. Varios módulos ejecutaban `CREATE TABLE`/inicialización de esquema durante el registro de rutas o durante requests. Un timeout dejaba la transacción PostgreSQL abortada y los módulos siguientes fallaban.
3. El inicio de Railway no separaba completamente la fase de migración del runtime Gunicorn.
4. El BAT local había regresado a un lanzador alterno y contenía mezcla CRLF/LF.
5. El expediente UCA únicamente consultaba `master_talento_humano`, aunque el módulo vigente utiliza `th_personas` y `th_asignaciones`.
6. La plantilla RAM empaquetada no coincidía con el formato oficial suministrado y openpyxl alteraba el XML de columnas ocultas al guardar.

## 3. Correcciones aplicadas

### PostgreSQL y despliegue

- Introspección de `information_schema.columns` limitada a la tabla solicitada.
- `rollback()` automático ante fallas SQLAlchemy/DBAPI antes de continuar.
- Separación explícita: migración con DDL habilitado → runtime con DDL deshabilitado.
- Guard común `runtime_schema.py` para impedir DDL en requests/workers.
- Facturación, Panel Comercial y Base Maestra ya no dependen de DDL por request.
- Gate de arranque que detiene el despliegue si falta un blueprint crítico.
- Endpoint `/api/system/version` y metadatos de build en health.

### Calendario y lista de chequeo

- Aislamiento por `fundacion_id` en eventos, previews, confirmaciones, evidencia y auditoría.
- El lector DOCX interpreta tablas con `N°`, `ACTIVIDAD`, `TH A CARGO` y `ENTREGA`.
- Las filas de componente se conservan como contexto.
- Una actividad sin fecha queda **pendiente de revisión**; no se inventan fechas.
- No se ejecuta DDL del calendario durante requests normales.

### RAM / listado oficial de asistencia

- Se incorporó la plantilla oficial suministrada con SHA-256 `a6b4c9412f7c72a19b9d5e842fa5ffd4b876c7d0f0c3d5c8e140b5287d700753`.
- Se actualizó el catálogo/manifiesto de plantillas oficiales.
- La generación toma fundación, UDS, participantes y talento humano desde la fuente de datos; no usa encabezados institucionales inventados.
- 20 participantes por hoja; 21 generan dos hojas.
- No se inventan marcas diarias de asistencia.
- Se preserva el XML de columnas, estilos, combinaciones, impresión y estructura visual del original.

### Windows y expediente UCA

- `INICIAR_PLATAFORMA_LOCAL.bat` vuelve a delegar en `scripts_windows\iniciar_plataforma.ps1 -Mode Local`.
- BAT local y de túnel quedaron con CRLF uniforme.
- Talento Humano del expediente usa `master_talento_humano` cuando existe y, en instalaciones actuales, `th_personas` + `th_asignaciones` como respaldo canónico.

## 4. Pruebas

- Compilación Python: **PASS**.
- Sintaxis JavaScript: **PASS, 43 archivos**.
- Integrity Gate: **PASS**.
- Suite crítica: **23/23 PASS**.
- Suite extendida: **40 PASS, 0 fallos funcionales, 5 bloqueadas únicamente porque este entorno no tenía Flask instalado**.
- Pruebas específicas: calendario/checklist real, aislamiento tenant, generación RAM con 21 participantes, preservación visual, continuidad de formatos, migraciones, autenticación concurrente, túnel/Windows, expediente UCA y ON CONFLICT.

## 5. Regla de honestidad de validación

Esta entrega es una **versión auditada y candidata a despliegue**. No es técnicamente responsable afirmar “100 % en producción” antes de desplegar este artefacto exacto en Railway y ejecutar smoke tests con la base PostgreSQL y credenciales reales. La suite local no detectó regresiones funcionales en las pruebas ejecutadas, pero el cierre de producción exige la validación indicada en la sección siguiente.

## 6. Validación obligatoria después de subir a GitHub/Railway

1. Confirmar el SHA/versión desde `/api/system/version`.
2. Confirmar `/health` o `/api/health` con HTTP 200.
3. Confirmar que los logs no contienen `QueryCanceled`, `InFailedSqlTransaction` ni la consulta global `ORDER BY table_name, ordinal_position`.
4. Probar login real y `/api/auth/me`.
5. Abrir calendario, importar el Word de checklist y comprobar vista previa sin fechas inventadas.
6. Generar listado oficial RAM para una UDS con 1, 20 y 21 participantes.
7. Probar Base Maestra, procesamiento de UDS, RPP, RAM/RAN/RRAN y Bienestarina.

## 7. Archivos modificados/nuevos

Total: **33**.

- **MODIFIED** `backend/app.py`
- **MODIFIED** `backend/generador_formatos.py`
- **MODIFIED** `backend/init_hosting.py`
- **MODIFIED** `backend/modules/calendario_inteligente/repository.py`
- **MODIFIED** `backend/modules/calendario_inteligente/routes.py`
- **MODIFIED** `backend/modules/calendario_inteligente/services.py`
- **MODIFIED** `backend/modules/centro_planeacion/repository.py`
- **MODIFIED** `backend/modules/dbapi_compat.py`
- **MODIFIED** `backend/modules/facturacion_suscripcion/repository.py`
- **MODIFIED** `backend/modules/facturacion_suscripcion/routes.py`
- **MODIFIED** `backend/modules/facturacion_suscripcion/services.py`
- **MODIFIED** `backend/modules/gestion_integral_uca/integrations.py`
- **MODIFIED** `backend/modules/panel_comercial/routes.py`
- **MODIFIED** `backend/modules/panel_comercial/services.py`
- **MODIFIED** `backend/modules/plantillas_oficiales.py`
- **NEW** `backend/modules/runtime_schema.py`
- **MODIFIED** `backend/seed_data/templates_originales/oficiales/plantilla_ram_oficial_v3.xlsx`
- **MODIFIED** `backend/seed_data/templates_originales/oficiales/templates_manifest.json`
- **MODIFIED** `backend/seed_data/templates_originales/seed_manifest.json`
- **MODIFIED** `backend/services/ram_v3_service.py`
- **NEW** `backend/tests/test_attendance_calendar_integration_v2_7_0.py`
- **NEW** `backend/tests/test_calendar_checklist_reader_v2_7_0.py`
- **NEW** `backend/tests/test_postgres_startup_regression_v2_7_0.py`
- **MODIFIED** `backend/tests/test_ram_v3_integration.py`
- **NEW** `docs/AUDITORIA_CORRECCIONES_PRIMERA_INFANCIA_v2_7_0.md`
- **NEW** `docs/AUDITORIA_PLANTILLA_RAM_V3.md`
- **NEW** `docs/GUIA_DESPLIEGUE_PRIMERA_INFANCIA_v2_7_0_AUDITADA.md`
- **NEW** `docs/MANIFIESTO_CAMBIOS_AUDITORIA_PRIMERA_INFANCIA_v2_7_0.json`
- **NEW** `docs/RESULTADOS_PRUEBAS_AUDITORIA_PRIMERA_INFANCIA_v2_7_0.json`
- **MODIFIED** `INICIAR_PLATAFORMA_LOCAL.bat`
- **MODIFIED** `integrity/baseline_v2_7_0.json`
- **MODIFIED** `integrity/critical_tests.json`
- **MODIFIED** `start_hosting.sh`

## 8. Estado final

**IMPLEMENTACIÓN CORREGIDA Y AUDITADA — SUITE CRÍTICA 23/23 PASS — SIN REGRESIONES FUNCIONALES DETECTADAS EN LAS PRUEBAS EJECUTADAS.**

## 9. Cierre QAP de Base Maestra y producción (2026-08-25)

Se completaron y desplegaron seis paquetes incrementales de corrección:

- **QAP1:** consolidación de UDS, asignación de docentes/coordinadores y proyecciones de talento humano.
- **QAP2:** consumidores de RAM, Planeación, Psicosocial, Familias y Redes, cruces y selectores RPP/Bienestarina.
- **QAP3:** generadores RAM, RAN, RPP y Bienestarina alimentados por la versión maestra activa.
- **QAP4:** alertas de edad, nutrición, cobertura y duplicados identificadas por documento y fundación.
- **QAP5:** registro manual de peso/talla resuelto desde `master_ninos`, sin cruzar llaves históricas.
- **QAP6:** reporte nutricional mensual desde la última `sn_valoraciones` por documento, período y tenant.

Regla resultante: cuando existe una Base Maestra publicada, esa versión es autoritativa y una UDS vacía no vuelve a poblarse desde tablas antiguas. Los respaldos `usuarios`/`beneficiarios` solo operan en instalaciones sin versión publicada o como proyecciones de compatibilidad expresamente delimitadas.

Validación QAP7:

- Integrity Gate: archivos, módulos, rutas, roles, 9 familias de formatos y baseline funcional: **PASS**.
- Sintaxis: **357 Python** y **45 JavaScript PASS**.
- PostgreSQL: **1.924 consultas revisadas; 0 no soportadas; 0 contratos faltantes**.
- Suite crítica y pruebas QAP1–QAP6: **PASS**.
- Railway: despliegue `02306c62-8b2c-4e9f-8228-24932a1dc96b` en estado **SUCCESS**.
- Smoke test público `/api/health`: **HTTP 200**, `database_backend=postgresql`, `database=ok`, SHA `1472e3cca5ba06fa5c7f9d235de00c6493851b96`.
- `/api/system/version` sin credenciales: **HTTP 401 esperado** por protección de autenticación.

El validador de empaquetado histórico no se utilizó como criterio de producción porque su baseline de hashes antecede estas correcciones y el workspace contiene datos runtime locales que no deben borrarse. La validación funcional, de integridad, PostgreSQL y el smoke test del artefacto desplegado sí quedaron completados.

**CIERRE TÉCNICO QAP7: CORRECCIONES DESPLEGADAS, INTEGRIDAD FUNCIONAL APROBADA Y PRODUCCIÓN OPERATIVA.**
