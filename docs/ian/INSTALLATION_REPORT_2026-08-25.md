# Reporte de instalación y corrección de IAN

Fecha: 25 de agosto de 2026  
Entorno verificado: Railway productivo  
Asistente activo: IAN

## Resultado

IAN quedó integrado como un único asistente modular. Cerrado muestra únicamente su silueta junto a accesibilidad; abierto muestra el panel, configuración, conversación y recorridos. El avatar usa un SVG multicapa con boca, ojos, cabeza, brazos, cuerpo y tablet independientes.

## Causas corregidas

| Problema | Causa confirmada | Corrección |
|---|---|---|
| IAN no aparecía | `.liam-tab span { display:none }` ocultaba el contenedor SVG | Regla específica `display:block!important` y prueba visual obligatoria |
| IAN quedaba detrás de accesibilidad | Ambos controles compartían el mismo espacio fijo | Silueta posicionada de forma adyacente con prueba geométrica |
| Accesibilidad tapaba el panel | El botón permanecía encima de los controles inferiores | Reubicación inmediata en escritorio y ocultamiento temporal en móvil |
| Mano y boca no respondían al abrir pronto | El runtime avanzado se cargaba de forma diferida | Estados `data-runtime-ready` y `data-profile-ready` |
| Mujer volvía a Hombre | Respuesta inicial atrasada sobrescribía el selector | Sincronización de perfil antes de habilitar pruebas/cambios |
| Voz seleccionada no se aplicaba | El selector solo persistía el valor | Selección de voz española disponible, género y velocidad aplicados al sintetizador |
| Nombre mezclado LIAM/ELIAN/IAN | Quedaban textos y valores predeterminados antiguos | Nombre predeterminado y mensajes normalizados a IAN |

## Funciones verificadas

- Silueta visible y adyacente a accesibilidad.
- Panel abre, cierra y restaura la silueta.
- Hombre y mujer.
- Variantes institucional, tecnológica y educativa.
- Persistencia por fundación y autorización por rol.
- Saludo con brazo independiente (`ian-wave`).
- Boca controlada por secuencia fonética; pausa la cierra.
- Avatar de recorrido separado del panel.
- Señalamiento, línea guía, teletransportación y caminata por anclajes.
- Diseño de escritorio y celular sin superposición.
- Recorrido institucional de 18 módulos.
- Progreso aislado por tenant, usuario y versión del recorrido.
- Voz, labios, caminata, animación y recorrido activados mediante variables Railway.

## Pruebas

| Grupo | Resultado |
|---|---|
| Playwright: visibilidad, apertura, cierre y adyacencia | Aprobado |
| Playwright: género, variante, gesto, labios y movimiento | Aprobado |
| Playwright: celular y panel responsive | Aprobado |
| Multi-tenant y roles de configuración/recorrido | Aprobado |
| 12 contratos LÍA/LIAM/ELIAN/IAN | Aprobado |
| Base Maestra y consumidores | Aprobado |
| Calendario y Centro Documental | Aprobado |
| Motor IDP | Aprobado |
| Formatos y RPP | Aprobado |
| Responsive | Aprobado |
| Health check previo a Railway | Aprobado |

La compuerta global `tools/validate_release.py` no pudo finalizar en Windows porque intenta ejecutar `bash`. Antes de ese punto confirmó 384 archivos Python con sintaxis válida. También reportó artefactos preexistentes del repositorio (SQLite, cachés, respaldo y hashes históricos); no se eliminaron para evitar pérdida de datos fuera del alcance de IAN.

## Evidencias

- `evidence/ian-launcher-production.png`
- `evidence/ian-panel-production.png`
- `evidence/ian-female-technological-guiding.png`
- `tools/ian-visibility.spec.js`
- `tools/ian-interactions.spec.js`

## Rollback

La desactivación funcional se realiza con `ENABLE_IAN_ASSISTANT=false`. Las funciones avanzadas pueden desactivarse individualmente con `LIAM_VOICE_ENABLED`, `LIAM_LIP_SYNC_ENABLED`, `LIAM_WALK_ENABLED`, `LIAM_ANIMATION_ENABLED` y `ELIAN_PLATFORM_TOUR_ENABLED`, sin afectar login, Base Maestra, calendario, formatos ni descargas.
