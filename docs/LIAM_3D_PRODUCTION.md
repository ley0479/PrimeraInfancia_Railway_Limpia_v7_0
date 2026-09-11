# LIAM 3D: operación y despliegue

## Estado de entrega

LIAM utiliza un modelo semirrealista riggeado con siete animaciones corporales y
faciales. La integración es progresiva: el avatar 2D institucional se dibuja
primero y solo se sustituye cuando el visor 3D termina de cargar correctamente.

## Activación segura

La función está apagada por defecto. Para un despliegue controlado:

1. Configurar `LIAM_AVATAR_3D_ENABLED=true` en el entorno del servicio.
2. Mantener `ENABLE_LIAM_ASSISTANT=true`.
3. Desplegar y comprobar `/assets/lia/3d/liam-semireal-v5.glb` con estado HTTP 200.
4. Abrir LIAM en escritorio y móvil y ejecutar Saludar, Señalar y Hablar.
5. Confirmar que voz, cierre del panel y cambio de orientación no dejan audio ni
   recursos gráficos activos.

## Selección adaptativa

El 3D no se inicia cuando hay reducción de movimiento, ahorro de datos, menos de
4 GB de memoria informada, menos de cuatro procesadores lógicos o ausencia de
WebGL. Cerrar el panel pausa y elimina el visor, liberando su modelo de la página.
En cualquier fallo de carga permanece visible el avatar 2D.

En pantallas de hasta 768 px el encuadre prioriza torso y rostro; en escritorio
se presenta el cuerpo completo. El GLB no se descarga hasta abrir el panel.

## Reversión

Cambiar `LIAM_AVATAR_3D_ENABLED=false` y reiniciar el servicio. No requiere borrar
activos ni cambiar datos: LIAM continúa funcionando con el respaldo 2D y voz.

## Verificación

```powershell
py -3 backend/tests/test_liam_3d_progressive_contract_v7.py
node tools/liam_3d/test_renderer_capability.js
node --check frontend/js/liam/liam-3d-renderer.js
```

La verificación profunda del GLB se ejecuta con Blender:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' --background --python tools/liam_3d/validate_liam_glb.py -- frontend/assets/lia/3d/liam-semireal-v5.glb
```

El laboratorio manual está en `frontend/theme-lab/liam-3d.html`.
