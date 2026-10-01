# Control de cambio — fotografía fija del login

- Solicitud y autorización: el responsable funcional adjuntó `LEISON.png`, pidió colocarla fija en el login y autorizó desplegar.
- Alcance: incorporar una copia local de la imagen y mostrarla únicamente en `#login-screen`.
- Archivos: `frontend/assets/branding/leison-login.png` y bloque inicial del login en `frontend/index.html`.
- Exclusiones: menú, Liam, logo configurable de cada fundación, autenticación, permisos y formularios.
- Huella SHA-256 del adjunto incorporado: `8e2d8d87468cd446a9ddc20b87ef629505c74a088e69c28d6d3832c17e3dc75a`.
- Reversión: retirar exclusivamente el elemento `#login-leison-photo` y el activo correspondiente.
- Pruebas: existencia/carga del activo, visibilidad del login, accesibilidad del texto alternativo, viewport móvil y regresión de autenticación.
- Publicación: autorizada junto con la Caracterización F23 el 30 de septiembre de 2026.
