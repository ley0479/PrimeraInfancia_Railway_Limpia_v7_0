# Auditoría correctiva RPP sin Minuta Patrón

Fecha: 26 de agosto de 2026

## Causa raíz confirmada

El frontend sí ejecutaba la descarga y enviaba unidad, categoría estable, mes, año y token. El endpoint `/api/rpp/descargar` detenía el flujo antes del generador cuando `obtener_minuta_vigente(...)` no encontraba una minuta compatible y respondía HTTP 422. Por tanto, la causa primaria no era ELIAN ni la plantilla: era una dependencia obligatoria de Minuta Patrón en el endpoint RPP.

## Diagnóstico del clic

| Flujo | Solicitud | Parámetros | Capa visual |
| --- | --- | --- | --- |
| RPP por categoría | `GET /api/rpp/descargar` | unidad, grupo, mes y año | ELIAN usa `pointer-events: none`; solo sus controles aceptan clic |

## Dependencia de Minuta Patrón

| Archivo | Función | Antes | Después |
| --- | --- | --- | --- |
| `backend/app.py` | `descargar_rpp_por_categoria` | Consultaba `obtener_minuta_vigente` y devolvía 422 | No consulta minuta; usa Base Maestra y plantilla oficial |
| `backend/services/rpp_minutas_service.py` | Funciones propias de minuta | Disponible | Sin modificación |

## Flujo vigente

Autenticación → tenant/fundación → unidad → periodo → categoría → participantes de Base Maestra → plantilla oficial RPP → copia generada → validación física → descarga.

Configuración predeterminada:

```env
RPP_SOURCE_MODE=official_template
RPP_REQUIRE_MINUTA_PATRON=false
RPP_ENABLE_MINUTA_ENRICHMENT=false
```

## Categorías verificadas con archivo real

| Categoría técnica | Resultado local |
| --- | --- |
| `0_6_GESTANTES` | Excel generado y abierto |
| `6_11_MESES` | Excel generado y abierto |
| `1_2_ANOS` | Excel generado y abierto |
| `3_5_ANOS` | Excel generado y abierto |

La prueba conserva nombres de hojas, fórmula oficial y área de impresión. Usa datos ficticios y no expone participantes reales.

## Archivos modificados

| Archivo | Cambio | Riesgo |
| --- | --- | --- |
| `backend/app.py` | Retira exclusivamente el requisito de minuta del endpoint RPP y agrega errores estructurados | Bajo, limitado a RPP |
| `.env.example` | Documenta el modo oficial sin minuta | Bajo |
| `backend/tests/test_rpp_generation_flow_v2_7_3.py` | Actualiza el contrato correcto | Bajo |
| `backend/tests/test_rpp_official_template_no_minuta_v2_7_4.py` | Prueba cuatro categorías, plantilla y overlays | Bajo |

## Rollback

Revertir únicamente el commit de esta corrección. No eliminar tablas, archivos ni endpoints de Minuta Patrón. La plantilla oficial nunca se sobrescribe.

## Límite de evidencia

La prueba automática abre archivos con OpenPyXL y valida estructura. La descarga con datos productivos y capturas autenticadas requiere una sesión y UDS reales autorizadas; no se inventan ni se exponen datos para simularla.
