# Contexto

El contexto confirmado procede del endpoint autenticado y contiene rol, módulos permitidos y guía de la sección actual. El frontend observa cambios de hash y cancela voz/resaltados. Pestaña, modal y control activo todavía requieren adaptadores específicos por pantalla.
# Contexto visible

LIAM recopila el módulo derivado de la navegación, la pestaña visible, el modal abierto y el control de ayuda enfocado. Estos datos solo orientan la interfaz; el rol, el tenant y los permisos se resuelven y validan en el backend autenticado.

