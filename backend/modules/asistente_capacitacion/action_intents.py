"""Deteccion conservadora de acciones solicitadas a LIAM.

Las acciones mutables nunca se ejecutan desde el modelo: se convierten en una
propuesta cerrada que el usuario debe confirmar en la interfaz.
"""
from __future__ import annotations

import re
import unicodedata

MONTHS = {
    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
    'julio': 7, 'agosto': 8, 'septiembre': 9, 'setiembre': 9, 'octubre': 10,
    'noviembre': 11, 'diciembre': 12,
}
GROUPS = (
    (('0 a 6', '0-6', 'gestante'), '0_6_GESTANTES', '0 a 6 meses y gestantes'),
    (('6 a 11', '6-11'), '6_11_MESES', '6 a 11 meses'),
    (('1 a 2', '1-2'), '1_2_ANOS', '1 a 2 años'),
    (('3 a 5', '3-5'), '3_5_ANOS', '3 a 5 años'),
)
MODULE_ALIASES = (
    (('calendario', 'agenda'), 'calendario-inteligente', 'Calendario Inteligente'),
    (('rpp', 'formato', 'formatos'), 'formatos', 'Formatos ICBF'),
    (('bienestarina',), 'formatos', 'Formatos ICBF'),
    (('base maestra',), 'base-maestra', 'Base Maestra'),
    (('beneficiario', 'beneficiarios', 'nino', 'nina'), 'buscador-beneficiarios', 'Buscador de beneficiarios'),
    (('talento humano', 'docentes'), 'talento', 'Talento Humano'),
    (('salud', 'nutricion'), 'salud-nutricion', 'Salud y Nutrición'),
    (('manual',), 'manual-operativo', 'Manual Operativo'),
    (('dashboard', 'inicio'), 'dashboard', 'Inicio'),
)


def _plain(value: object) -> str:
    value = unicodedata.normalize('NFKD', str(value or '').casefold())
    return ''.join(char for char in value if not unicodedata.combining(char))


def _clean_unit(value: object) -> str:
    value = re.sub(r'\s+', ' ', str(value or '')).strip(' .,;:-')
    return value[:120]


def propose_action(question: str, *, screen_context: dict | None = None) -> dict | None:
    """Devuelve una propuesta estructurada; nunca ejecuta la accion."""
    q = _plain(question)
    context = screen_context if isinstance(screen_context, dict) else {}
    if any(word in q for word in ('abre', 'abrir', 'llevame', 'ir a', 've a')):
        for aliases, module, label in MODULE_ALIASES:
            if any(alias in q for alias in aliases):
                return {'id':'open_module','label':f'Abrir {label}','summary':f'Abriré {label}.','arguments':{'module':module},'missing':[],'confirmation_required':False,'client_handler':'open_module'}
    if any(word in q for word in ('pendiente', 'pendientes', 'por entregar', 'vencimiento')) and any(word in q for word in ('entrega', 'entregable', 'actividad', 'calendario', 'tengo', 'muestra', 'dime')):
        return {'id':'get_pending_activities_summary','label':'Consultar pendientes','summary':'Consultaré tus actividades pendientes autorizadas.','arguments':{},'missing':[],'confirmation_required':False,'server_tool':'get_pending_activities_summary'}
    document_match=re.search(r'\b(?:documento|cedula|identificacion|nui)\s*(?:numero|nro|no)?\s*[:#-]?\s*(\d{5,15})\b',q)
    if document_match and any(word in q for word in ('busca', 'buscar', 'muestra', 'consulta', 'consultar')):
        return {'id':'search_beneficiary','label':'Buscar beneficiario','summary':'Abriré la búsqueda autorizada del beneficiario.','arguments':{'query':document_match.group(1),'module':'buscador-beneficiarios'},'missing':[],'confirmation_required':False,'client_handler':'search_beneficiary'}
    version_match=re.search(r'\bversion\s*(?:id|numero|nro|no)?\s*[:#-]?\s*(\d+)\b',q)
    if 'base maestra' in q and any(word in q for word in ('publica','publicar')):
        version_id=int(version_match.group(1)) if version_match else None
        return {'id':'publish_master_database','label':'Confirmar publicación','summary':f"Publicar la versión {version_id or 'indicada'} de Base Maestra.",'arguments':{'version_id':version_id,'module':'base-maestra'},'missing':[] if version_id else ['número de versión'],'confirmation_required':True,'client_handler':'publish_master_database'}
    if 'base maestra' in q and any(word in q for word in ('consolida','consolidar')):
        return {'id':'consolidate_master_database','label':'Confirmar consolidación','summary':'Consolidar las fuentes pendientes y crear una nueva versión de Base Maestra.','arguments':{'module':'base-maestra'},'missing':[],'confirmation_required':True,'client_handler':'consolidate_master_database'}
    if re.search(r'\b(?:crea|crear)\s+(?:un\s+)?usuario\b',q):
        username_match=re.search(r'\busuario(?:name)?\s+([a-z0-9._-]{3,50})',q)
        email_match=re.search(r'\b(?:correo|email)\s+([^\s,;]+@[^\s,;]+)',q)
        role_match=re.search(r'\brol\s+(superadmin|gerente|coordinador|docente|nutricionista|psicosocial|auxiliar administrativo)\b',q)
        foundation_id_match=re.search(r'\bfundacion\s*(?:id|numero|nro|no)?\s*[:#-]?\s*(\d+)\b',q)
        role=(role_match.group(1).replace(' ','_').upper() if role_match else None)
        arguments={'username':username_match.group(1) if username_match else None,'email':email_match.group(1) if email_match else None,'role':role,'foundation_id':int(foundation_id_match.group(1)) if foundation_id_match else None,'module':'administracion'}
        missing=[label for key,label in (('username','nombre de usuario'),('email','correo'),('role','rol'),('foundation_id','ID de fundación')) if not arguments[key]]
        return {'id':'create_user','label':'Confirmar creación de usuario','summary':f"Crear el usuario {arguments['username'] or 'indicado'} con rol {role or 'pendiente'}.",'arguments':arguments,'missing':missing,'confirmation_required':True,'client_handler':'create_user'}
    if re.search(r'\b(?:crea|crear)\s+(?:una\s+)?fundacion\b',q):
        name_match=re.search(r'\bfundaci[oó]n\s+(?:llamada|nombre)\s+(.+?)(?=\s+(?:con\s+)?(?:nit|correo|email|plan)\b|$)',question,re.I)
        name=_clean_unit(name_match.group(1)) if name_match else None
        nit_match=re.search(r'\bnit\s*[:#-]?\s*([0-9.-]{5,20})\b',q)
        arguments={'name':name,'nit':nit_match.group(1) if nit_match else None,'module':'administracion'}
        return {'id':'create_foundation','label':'Confirmar creación de fundación','summary':f"Crear e inicializar la fundación {name or 'indicada'}.",'arguments':arguments,'missing':[] if name else ['nombre de fundación'],'confirmation_required':True,'client_handler':'create_foundation'}
    user_match=re.search(r'\busuario\s*(?:id|numero|nro|no)?\s*[:#-]?\s*(\d+)\b',q)
    if user_match and any(word in q for word in ('suspende','suspender','desactiva','desactivar','reactiva','reactivar')):
        activate=any(word in q for word in ('reactiva','reactivar'))
        return {'id':'update_user','label':'Confirmar cambio de usuario','summary':f"{'Reactivar' if activate else 'Suspender'} el usuario {user_match.group(1)}.",'arguments':{'user_id':int(user_match.group(1)),'active':activate,'module':'administracion'},'missing':[],'confirmation_required':True,'client_handler':'update_user'}
    foundation_match=re.search(r'\bfundacion\s*(?:id|numero|nro|no)?\s*[:#-]?\s*(\d+)\b',q)
    if foundation_match and any(word in q for word in ('suspende','suspender','desactiva','desactivar','reactiva','reactivar')):
        activate=any(word in q for word in ('reactiva','reactivar'))
        return {'id':'update_foundation','label':'Confirmar cambio de fundación','summary':f"{'Reactivar' if activate else 'Suspender'} la fundación {foundation_match.group(1)}.",'arguments':{'foundation_id':int(foundation_match.group(1)),'active':activate,'module':'administracion'},'missing':[],'confirmation_required':True,'client_handler':'update_foundation'}
    if 'ram' in q and any(word in q for word in ('genera','generar','descarga','descargar','saca','sacame')):
        month=next((number for name,number in MONTHS.items() if re.search(rf'\b{name}\b',q)),None)
        year_match=re.search(r'\b(20\d{2}|2100)\b',q);year=int(year_match.group(1)) if year_match else None
        unit=_clean_unit(context.get('selected_unit'))
        match=re.search(r'\b(?:de|para la (?:uds|unidad))\s+(.+?)(?=\s+(?:para|del|de)\s+(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre|20\d{2})\b|$)',question,re.I)
        if not unit and match:unit=_clean_unit(match.group(1))
        month=month or context.get('selected_month');year=year or context.get('selected_year')
        missing=[name for name,value in (('unidad',unit),('mes',month),('año',year)) if not value]
        return {'id':'download_ram','label':'Confirmar y generar RAM','summary':f"Generar y descargar el RAM de {unit or 'la UDS indicada'}"+(f", periodo {int(month):02d}/{int(year)}." if month and year else '.'),'arguments':{'unit':unit or None,'month':month,'year':year,'module':'formatos'},'missing':missing,'confirmation_required':True,'client_handler':'download_ram'}
    if 'rpp' not in q or not any(word in q for word in ('genera', 'generar', 'descarga', 'descargar', 'saca', 'sacame')):
        return None
    month = next((number for name, number in MONTHS.items() if re.search(rf'\b{name}\b', q)), None)
    try:
        year = int(re.search(r'\b(20\d{2}|2100)\b', q).group(1))
    except AttributeError:
        year = None
    group = group_label = None
    for aliases, code, label in GROUPS:
        if any(alias in q for alias in aliases):
            group, group_label = code, label
            break
    unit = _clean_unit(context.get('selected_unit'))
    match = re.search(r'\b(?:de|para la (?:uds|unidad))\s+(.+?)(?=\s+(?:para|del|de)\s+(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre|20\d{2})\b|$)', question, re.I)
    if not unit and match:
        unit = _clean_unit(match.group(1))
    month = month or context.get('selected_month')
    year = year or context.get('selected_year')
    missing = [name for name, value in (('unidad', unit), ('mes', month), ('año', year), ('grupo etario', group)) if not value]
    summary = f"Generar y descargar el RPP de {unit or 'la UDS indicada'}"
    if group_label:
        summary += f", grupo {group_label}"
    if month and year:
        summary += f", periodo {int(month):02d}/{int(year)}"
    return {
        'id': 'download_rpp', 'label': 'Confirmar y generar RPP', 'summary': summary + '.',
        'arguments': {'unit': unit or None, 'month': month, 'year': year, 'group': group},
        'missing': missing, 'confirmation_required': True, 'client_handler': 'download_rpp',
    }
