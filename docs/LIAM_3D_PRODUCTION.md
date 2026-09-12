# LIAM lector: integración visual

## Alcance

Esta entrega cambia solamente el perfil visual femenino del asistente LIAM por
el busto estático entregado en LIAM_Lector_Listo.zip. No incorpora el panel
liam-lector, speech-core.mjs, textos de demostración ni otro sintetizador.
El perfil masculino y todos los recursos visuales anteriores permanecen
disponibles.

El modelo no tiene esqueleto, clips ni morph targets. Por ello no se anuncian
Idle, Walk, Talk, sincronización labial ni movimiento de extremidades.

## Funcionamiento conservado

- liam-controller.js mantiene el botón, panel, chat, historial, accesos,
  selección de personaje/voz, explicación de pantalla y detección de módulo.
- speech-controller.js (window.LIA_SPEECH) sigue siendo la única autoridad de
  lectura, pausa, continuación, detención, voz elegida y velocidad.
- liam-state-machine.js comunica estados como speaking y listening; el avatar
  estático los representa mediante un indicador discreto.
- liam-movement-controller.js conserva posiciones, recorridos, límites y
  resaltados. Durante un recorrido mueve un PNG del mismo avatar; no crea otro
  contexto WebGL ni simula que el busto camina o señala.
- Cerrar el panel detiene voz, escucha, Realtime y recorridos, y libera el visor.
- La selección masculina continúa usando iam-hombre-v1.glb.

No se modificaron autenticación, sesiones, roles, aislamiento, créditos,
suscripciones, herramientas, Base Maestra ni lógica de negocio.

## Recursos y rutas reales

Flask sirve frontend mediante las rutas existentes de la aplicación. El
renderizador solicita solo una variante:

- Escritorio: /assets/lia/3d/liam-lector.glb (2.999.160 bytes).
- Móvil: /assets/lia/3d/liam-lector-movil.glb (1.262.084 bytes).
- Respaldo: /assets/lia/3d/liam-lector-frontal.png.
- Visor existente: /vendor/model-viewer/model-viewer-4.3.1.min.js.

No se añadió una segunda copia de model-viewer.

## Carga, encuadre y respaldo

La función sigue siendo progresiva y depende de LIAM_AVATAR_3D_ENABLED.
El modelo se carga al abrir el asistente, sin descargar simultáneamente las dos
variantes. La cámara usa el encuadre documentado por el paquete para el busto,
fondo transparente y luz neutral.

Si WebGL no está disponible se conserva la representación anterior. Si el GLB,
el motor o su render tardan más de 25 segundos, se muestra la imagen frontal
del paquete. El chat y la voz no dependen del resultado visual.

## Verificación

    python backend/tests/test_liam_3d_progressive_contract_v7.py
    node tools/liam_3d/test_renderer_capability.js
    node --check frontend/js/liam/liam-3d-renderer.js
    node --check frontend/js/liam/liam-movement-controller.js
    npx.cmd playwright test "tools/liam_3d/liam-production.spec.js" --workers=1

Las pruebas automatizadas comprueban estructura estática de ambos GLB, selección
escritorio/móvil, un único visor, estados visuales, liberación al cerrar, perfil
masculino, respaldo por error, movimiento mediante proxy y una sola llamada al
motor de voz existente. La voz de esas pruebas es simulada.

Pendiente antes de producción: confirmar audio audible con una voz real de
Windows, render WebGL interactivo en el equipo objetivo, teléfono físico y
prueba autenticada completa. No se realizó despliegue.

## Reversión

No es necesario borrar activos. Para volver al avatar anterior, cambiar en
frontend/js/liam/liam-3d-renderer.js las rutas female.desktop y female.mobile a
liam-produccion-v1.glb, retirar la clase específica liam-lector-ready y restaurar
la versión de caché del script. Como reversión operativa inmediata también puede
configurarse LIAM_AVATAR_3D_ENABLED=false; LIAM continuará con su representación
2D, chat y voz.
