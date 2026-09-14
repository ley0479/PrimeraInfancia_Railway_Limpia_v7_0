"""Adaptadores de notificación desacoplados y cerrados por defecto."""
from pathlib import Path
import sys
BACKEND=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BACKEND))
from modules.asistente_capacitacion.notification_providers import NotificationProvider,provider_catalog,get_provider

catalog=provider_catalog()
assert [item['channel'] for item in catalog]==['email','whatsapp']
assert all(not item['configured'] and not item['enabled'] and not item['send_supported'] and item['approval_required'] for item in catalog)
assert isinstance(get_provider('email'),NotificationProvider)
try:get_provider('email').send(recipients=[],subject='Prueba',message='No enviar')
except PermissionError:pass
else:raise AssertionError('El adaptador deshabilitado permitió un envío.')
try:get_provider('telegram')
except LookupError:pass
else:raise AssertionError('Se aceptó un proveedor fuera del registro.')
print('LIAM_NOTIFICATION_PROVIDERS_V7_PASS')
