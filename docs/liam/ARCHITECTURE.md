# Arquitectura LIAM

LIAM es una capa frontend aditiva sobre el blueprint seguro de LÍA. Reutiliza sesión, tenant, permisos, presentación, chat, herramientas de lectura, preferencias y auditoría. `ENABLE_LIAM_ASSISTANT` decide el montaje. Cuando está activo, el frontend visual anterior de LÍA no se monta.

Componentes: máquina de estados, registro de controles, registro de anclajes, zonas seguras, orquestador visual, movimiento, recorridos, tablet, lip sync básico y controlador. No se modificaron generadores ni módulos de negocio.

