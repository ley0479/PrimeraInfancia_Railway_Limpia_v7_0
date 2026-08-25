"""Respuesta estructurada, registro cerrado y redacción de LÍA."""
from pathlib import Path
import sys
BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
from modules.asistente_capacitacion.assistant_service import respond
from modules.asistente_capacitacion.privacy_service import redact

answer = respond(question='¿Dónde hago clic?', module='base-maestra', role='COORDINADOR')
assert answer['confidence'] == 'confirmed'
assert answer['actions'] == [
    {'type':'scroll_to','target':'base-maestra.open'},
    {'type':'highlight','target':'base-maestra.open'},
]
assert answer['provider'] == 'institutional_static'
assert redact('correo persona@example.com documento 123456789 y token=abc') == 'correo [CORREO] documento [IDENTIFICADOR] y [SECRETO REDACTADO]'
diagnostic = respond(question='¿Por qué falló?', module='motor-documental', role='DOCENTE')
assert diagnostic['confidence'] == 'insufficient'
print('LIA_ASSISTANT_SERVICE_V7_PASS')
