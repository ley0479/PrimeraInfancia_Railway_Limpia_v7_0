"""Motor estático verificable de LÍA; el proveedor de IA permanece opcional."""
from __future__ import annotations
import uuid
from .guides import DEFAULT_GUIDE, GUIDES
from .privacy_service import redact
from .platform_profile import get_platform_profile

def respond(*, question: str, module: str, role: str, allowed_modules=None) -> dict:
    guide = dict(GUIDES.get(module, DEFAULT_GUIDE))
    q = question.casefold()
    actions = []
    confidence = 'confirmed'
    profile = get_platform_profile()
    allowed_modules = list(allowed_modules or [])
    module_names = [GUIDES[key]['titulo'] for key in allowed_modules if key in GUIDES]
    if any(word in q for word in ('qué es esta plataforma', 'que es esta plataforma', 'para qué sirve', 'para que sirve')):
        message = (f'{profile["description"]} Sirve para centralizar la Base Maestra, el talento humano, '
                   'salud y nutrición, la gestión pedagógica y psicosocial, el calendario, las evidencias, '
                   'los formatos y el seguimiento autorizado, manteniendo separación por fundación y permisos por rol.')
    elif any(word in q for word in ('qué versión', 'que version', 'versión actual', 'version actual')):
        message = f'La versión configurada actualmente es {profile["version"]}.'
    elif any(word in q for word in ('qué módulos', 'que modulos', 'módulos tiene', 'modulos tiene')):
        message = (f'Para el rol {role or "actual"} hay {len(module_names)} módulos autorizados: ' + ', '.join(module_names) + '.') if module_names else 'No encontré módulos autorizados confirmados para esta sesión.'
    elif any(word in q for word in ('qué puedo hacer', 'que puedo hacer', 'según mi rol', 'segun mi rol')):
        message = (f'Tu rol actual es {role or "no identificado"}. Puedes consultar y usar únicamente estas áreas autorizadas: ' + ', '.join(module_names) + '. LÍA adapta las guías y herramientas a esos permisos.') if module_names else f'Tu rol actual es {role or "no identificado"}, pero no encontré áreas autorizadas confirmadas.'
    elif any(word in q for word in ('flujo general', 'cómo se utiliza la plataforma', 'como se utiliza la plataforma', 'cómo funciona la plataforma', 'como funciona la plataforma')):
        message = ('Flujo general: 1. Inicia sesión y confirma la fundación. 2. Carga o actualiza las fuentes autorizadas en Base Maestra. '
                   '3. Revisa unidades, participantes y talento humano. 4. Consulta el calendario y los entregables. '
                   '5. Trabaja en el módulo correspondiente. 6. Carga evidencias o genera borradores. '
                   '7. Revisa, confirma y descarga únicamente resultados validados por el sistema y el profesional responsable.')
    elif any(word in q for word in ('quién diseñó', 'quien diseño', 'quién creó', 'quien creo', 'fecha de creación', 'fecha de creacion', 'presenta la plataforma', 'presentar la plataforma')):
        if profile['identity_confirmed']:
            message = f'{profile["description"]} Fue diseñada por {profile["designer"]}, su fecha institucional de creación es {profile["created_date"]} y la versión actual es {profile["version"]}.'
        else:
            message = f'{profile["description"]} La autoría y la fecha de creación todavía no han sido confirmadas en la configuración institucional; no debo inventarlas.'
            confidence = 'insufficient'
    elif any(word in q for word in ('dónde', 'donde', 'clic', 'botón', 'boton')):
        message = f'Te mostraré el acceso registrado de {guide["titulo"]}. LÍA no pulsará ni guardará nada por ti.'
        actions = [{'type':'scroll_to','target':f'{module}.open'}, {'type':'highlight','target':f'{module}.open'}]
    elif any(word in q for word in ('error', 'falló', 'fallo', 'no carga', 'no descarga', 'validación')):
        message = ('Podemos revisarlo con calma. Todavía no hay información suficiente para confirmar la causa. '
                   'Primero revisa el código y mensaje exactos, el estado del proceso y los requisitos visibles. '
                   'Si compartes el error estructurado sin datos personales, podré orientarte con mayor precisión.')
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
        'suggestions': ['Conocer la plataforma', 'Explícame esta pantalla', 'Ver versión actual', 'Ver mis pendientes'],
        'actions': actions, 'diagnostic': None, 'request_id': uuid.uuid4().hex,
        'module': module, 'role': role, 'provider': 'institutional_static',
    }
