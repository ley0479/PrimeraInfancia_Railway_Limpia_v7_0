# Arquitectura de LÍA

LÍA es un módulo transversal independiente. Flask registra únicamente el
blueprint `modules/asistente_capacitacion`; el frontend carga un inicializador,
un registro cerrado de controles y estilos propios. Con
`ENABLE_LIA_ASSISTANT=false` no se monta ningún elemento visual ni se consulta
contexto autenticado.

La versión inicial usa ayuda institucional curada y herramientas de lectura ya
autorizadas. IA externa, voz de backend y Realtime permanecen desacoplados y
apagados hasta configurar proveedor, permisos, auditoría y pruebas.

El avatar humano provisional vive en `frontend/assets/lia/lia-human-v1.png` y
su controlador expone estados independientes de la imagen. El recurso generado
conservó un fondo oscuro pese a solicitar transparencia; se integra en un marco
oscuro y deberá reemplazarse por el `.riv` o PNG transparente definitivo sin
modificar el controlador.

Flujo seguro: contexto autenticado → guía permitida por rol → respuesta de texto
escapada → acción visual registrada. LÍA no ejecuta guardados ni operaciones
misionales.
