# LIAM 3D para web

Artefacto activo: `liam-semireal-v5.glb`.

- Tamaño: 2.96 MB (límite de aceptación: 3 MB decimales).
- Geometría importada: 42.976 triángulos, 24 mallas y un armature.
- Clips: `Idle`, `Walk`, `Wave`, `Point`, `Talk`, `Listen` y `Think`.
- La acción `Talk` incluye movimiento de mandíbula/labios y gestos corporales.
- Textura corporal reducida a 1024 x 1024 para la entrega web.

La base humana y su textura proceden de MPFB/MakeHuman. Los activos del paquete
MakeHuman System Assets utilizados para esta generación son CC0. El GLB es una
salida generada y puede utilizarse en la plataforma. La fuente editable está en
`tools/liam_3d/source/liam-semireal-v5.blend` y el constructor reproducible en
`tools/liam_3d/build_liam_semireal_v5.py`.

No se debe servir el archivo `.blend` al navegador. El frontend carga únicamente
el GLB y el motor local `model-viewer`.
