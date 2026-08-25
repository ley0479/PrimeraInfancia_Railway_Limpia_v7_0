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
allowed = ['dashboard', 'base-maestra', 'calendario-inteligente']
purpose = respond(question='¿Qué es esta plataforma y para qué sirve?', module='dashboard', role='COORDINADOR', allowed_modules=allowed)
assert 'gestión integral' in purpose['message'] and 'Base Maestra' in purpose['message']
modules = respond(question='¿Qué módulos tiene?', module='dashboard', role='COORDINADOR', allowed_modules=allowed)
assert '3 módulos autorizados' in modules['message'] and 'Calendario inteligente' in modules['message']
role = respond(question='¿Qué puedo hacer según mi rol?', module='dashboard', role='COORDINADOR', allowed_modules=allowed)
assert 'COORDINADOR' in role['message'] and 'Base Maestra' in role['message']
workflow = respond(question='¿Cuál es el flujo general de trabajo?', module='dashboard', role='COORDINADOR', allowed_modules=allowed)
assert 'Inicia sesión' in workflow['message'] and 'Carga evidencias' in workflow['message']
version = respond(question='¿Cuál es la versión actual?', module='dashboard', role='COORDINADOR', allowed_modules=allowed)
assert '2.7.2-document-center' in version['message']
print('LIA_ASSISTANT_SERVICE_V7_PASS')
