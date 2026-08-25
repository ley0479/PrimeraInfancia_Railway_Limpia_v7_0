# Arquitectura de LÍA

LÍA es un módulo transversal independiente. Flask registra únicamente el
blueprint `modules/asistente_capacitacion`; el frontend carga un inicializador,
un registro cerrado de controles y estilos propios. Con
`ENABLE_LIA_ASSISTANT=false` no se monta ningún elemento visual ni se consulta
contexto autenticado.

La versión inicial usa ayuda institucional curada y herramientas de lectura ya
autorizadas. IA externa, voz de backend y Realtime permanecen desacoplados y
apagados hasta configurar proveedor, permisos, auditoría y pruebas.

Flujo seguro: contexto autenticado → guía permitida por rol → respuesta de texto
escapada → acción visual registrada. LÍA no ejecuta guardados ni operaciones
misionales.
