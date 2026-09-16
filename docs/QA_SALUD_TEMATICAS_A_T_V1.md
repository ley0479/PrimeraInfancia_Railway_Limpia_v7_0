# Matriz QA — Salud y Nutrición, temáticas e informes

Fecha de ejecución: 2026-09-16. Entorno: desarrollo local. Producción no probada ni desplegada.

| Caso | Estado | Evidencia / límite |
|---|---|---|
| A. Afiche real → tres temas | **NO VERIFICADO** | El archivo visual real no está disponible. Fixture textual: PASS, sin presentarlo como lectura visual. |
| B. No inventar periodo/unidad/ejecución | **PASS** | `test_salud_tematicas_phase1_v1.py`; publicar y generar borrador conservan campos ausentes. |
| C. 2019 no es fecha; norma no certificada | **PASS** | Referencia `vigencia_verificada=false`; test contractual. |
| D. Imagen borrosa requiere revisión | **PASS** | `test_idp_documental_core_v1.py`; control de calidad IDP. |
| E. Archivo sin temas | **PASS** | Resultado vacío y advertencia `SIN_CONTENIDO_TEMATICO_IDENTIFICADO`. |
| F. Reintento no duplica | **PASS** | Hash IDP, unicidades de publicación, calendario e informe/snapshot. |
| G. Unidades comparten material, ejecuciones separadas | **PASS** | Asignación por unidad; actividad/evidencia referencian una unidad/actividad independiente. |
| H. Mes sin día queda sin programar | **PASS** | `SIN_PROGRAMAR`; calendario solo se crea cuando existe día confirmado. |
| I. Varios temas no multiplican asistentes | **PASS** | Tabla M:N `sn_actividad_temas`; asistencia permanece en `sn_actividad_participantes`. |
| J. Informe sin ejecución incompleto | **PASS** | Snapshot exige fecha real, metodología y resultados reportados. |
| K. Asistencia desde listado vinculado | **PASS** | Conteos consultan participantes de la actividad, no Base Maestra activa. |
| L. Plantilla institucional legible y descarga | **NO VERIFICADO** | Descarga e integridad internas: PASS. Falta plantilla institucional vacía aprobada para cotejo visual final. |
| M. Corregir tema no altera informe aprobado | **PASS** | Informe congela snapshot/hash; cambios posteriores generan otra versión. |
| N. Aislamiento tenant/unidad/descarga | **PASS** | `test_multitenant_release_v2_4_0.py`, `test_descarga_directa_tenant_v2_7_0.py` y pruebas Liam. |
| O. Cambio tras confirmar revalida | **PASS** | Publicación valida periodo/unidades actuales; revisión temática usa control optimista. |
| P. Instrucciones maliciosas no ejecutan herramientas | **PASS** | `test_liam_prompt_injection_boundary_v7.py`; extracción se trata como datos. |
| Q. Sin API funciona manual/exportación determinística | **PASS** | Temas manuales, actividades y PDF/XLSX internos no dependen de proveedor IA. |
| R. Facturación sin reintentos infinitos | **NO VERIFICADO** | El flujo temático no consume proveedor generativo; no se probó una cuenta externa con saldo agotado. |
| S. Revisores simultáneos reciben conflicto | **PASS** | `revision` requerida; versión desactualizada devuelve HTTP 409. |
| T. Móvil, teclado y sin Liam | **IMPLEMENTADO / NO VERIFICADO VISUALMENTE** | HTML responsive, controles nativos y flujo independiente de Liam; falta recorrido manual multidispositivo. |

## Comandos ejecutados

```text
python backend/tests/test_salud_tematicas_phase1_v1.py
python backend/tests/test_idp_security_limits_v1.py
python backend/tests/test_idp_documental_core_v1.py
python backend/tests/test_salud_nutricion_integral_v2_6_0.py
python backend/tests/test_salud_nutricion_informes_actas_v7.py
python backend/tests/test_entregables_salud_nutricion_informe_mensual_v7.py
python backend/tests/test_centro_documental_core_v7.py
python backend/tests/test_centro_documental_integrations_v7.py
python backend/tests/test_base_maestra_http_contract.py
python backend/tests/test_multitenant_release_v2_4_0.py
python backend/tests/test_descarga_directa_tenant_v2_7_0.py
python backend/tests/test_calendar_phase1_views_v2_7_0.py
python backend/tests/test_calendar_phase2_recurrence_v2_7_0.py
python backend/tests/test_calendar_phase3_checklist_v2_7_0.py
python backend/tests/test_attendance_calendar_integration_v2_7_0.py
python backend/tests/test_lia_tool_registry_v7.py
python backend/tests/test_liam_action_intents_v7.py
python backend/tests/test_liam_action_policy_v7.py
python backend/tests/test_liam_prompt_injection_boundary_v7.py
node --check frontend/js/modules/salud-nutricion.js
node --check frontend/js/liam/liam-controller.js
git diff --check
```

## Bloqueos para cierre institucional

1. Adjuntar el afiche real para la prueba visual A.
2. Proporcionar o identificar la plantilla institucional vacía aprobada para el informe; los archivos actuales permanecen rotulados como borradores internos.
3. Realizar validación visual manual en móvil/tablet y del documento renderizado.
4. El despliegue productivo requiere autorización específica, respaldo según el procedimiento vigente y verificación posterior.
