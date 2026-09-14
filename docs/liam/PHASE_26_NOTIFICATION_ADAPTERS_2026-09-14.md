# Fase 26: adaptadores de correo y WhatsApp

## Resultado

Se define `NotificationProvider` y adaptadores separados `EmailProvider` y `WhatsAppProvider`. Los borradores de Liam informan los canales disponibles y la API expone su estado sin credenciales.

## Seguridad

- Ambos proveedores están desconfigurados y deshabilitados por defecto.
- `send()` rechaza cualquier intento mientras no exista un adaptador real autorizado.
- Preparar un borrador no implica enviarlo.
- Un proveedor futuro deberá declarar configuración, soporte de envío y aprobación obligatoria.
- Liam no está acoplado a ningún proveedor externo.

## Archivos, pruebas y rollback

Se agrega `notification_providers.py`, su prueba y un endpoint autenticado de estado. Se amplía la tarjeta de comunicaciones. No hay migraciones ni variables nuevas. El rollback consiste en revertir el commit de esta fase.
