# Configuración de LÍA

La bandera maestra es `ENABLE_LIA_ASSISTANT=false`. Las banderas secundarias no
pueden activar funciones si la maestra está apagada. Consulte `.env.example`
para el catálogo sin valores secretos.

Orden recomendado: activar interfaz y ayuda contextual; validar un tenant
piloto; habilitar voz; por último configurar IA o Realtime. Los nombres de
modelos y credenciales pertenecen exclusivamente al entorno del servidor.

La presentación institucional usa `LIA_PLATFORM_DESIGNER`,
`LIA_PLATFORM_CREATED_DATE` y `LIA_PLATFORM_DESCRIPTION`. Si autoría o fecha
están vacías, LÍA declara que no han sido confirmadas y nunca las inventa.
