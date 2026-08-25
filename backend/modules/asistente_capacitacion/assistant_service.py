"""Motor estático verificable de LÍA; el proveedor de IA permanece opcional."""
from __future__ import annotations
import uuid
from .guides import DEFAULT_GUIDE, GUIDES
from .privacy_service import redact
from .platform_profile import get_platform_profile

def respond(*, question: str, module: str, role: str) -> dict:
    guide = dict(GUIDES.get(module, DEFAULT_GUIDE))
    q = question.casefold()
    actions = []
    confidence = 'confirmed'
    if any(word in q for word in ('quién diseñó', 'quien diseño', 'quién creó', 'quien creo', 'fecha de creación', 'fecha de creacion', 'presenta la plataforma', 'presentar la plataforma')):
        profile = get_platform_profile()
        if profile['identity_confirmed']:
            message = f'{profile["description"]} Fue diseñada por {profile["designer"]} y su fecha institucional de creación es {profile["created_date"]}.'
        else:
            message = f'{profile["description"]} La autoría y la fecha de creación todavía no han sido confirmadas en la configuración institucional; no debo inventarlas.'
            confidence = 'insufficient'
    elif any(word in q for word in ('dónde', 'donde', 'clic', 'botón', 'boton')):
        message = f'Te mostraré el acceso registrado de {guide["titulo"]}. LÍA no pulsará ni guardará nada por ti.'
        actions = [{'type':'scroll_to','target':f'{module}.open'}, {'type':'highlight','target':f'{module}.open'}]
    elif any(word in q for word in ('error', 'falló', 'fallo', 'no carga', 'no descarga', 'validación')):
        message = ('Información insuficiente para confirmar la causa. Revisa el código y mensaje exactos, '
                   'el estado del proceso y los requisitos visibles. Comparte el error estructurado sin datos personales.')
        confidence = 'insufficient'
    elif any(word in q for word in ('cómo', 'como', 'paso', 'qué hago', 'que hago', 'pantalla')):
        message = f'{guide.get("proposito", guide["resumen"])}\n' + '\n'.join(f'{i}. {step}' for i, step in enumerate(guide.get('pasos', []), 1))
    else:
        message = (f'Estás en {guide["titulo"]}. Puedo explicar esta pantalla, mostrar el acceso registrado, '
                   'orientarte paso a paso o ayudarte a interpretar un error confirmado por la plataforma.')
    safe = redact(message)
    return {
        'message': safe, 'speech_text': safe, 'avatar_state': 'guiding' if actions else 'idle',
        'severity': 'info', 'confidence': confidence, 'confirmation_required': False,
        'suggestions': ['Explícame esta pantalla', 'Muéstrame dónde', 'Ver mis pendientes'],
        'actions': actions, 'diagnostic': None, 'request_id': uuid.uuid4().hex,
        'module': module, 'role': role, 'provider': 'institutional_static',
    }
