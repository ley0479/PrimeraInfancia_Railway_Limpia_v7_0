"""Motor conversacional verificable de LIAM con recuperación del Manual Maestro."""
from __future__ import annotations
import re, unicodedata, uuid
from .guides import DEFAULT_GUIDE, GUIDES
from .privacy_service import redact
from .platform_profile import get_platform_profile

STOP = frozenset("a al como con cual de del donde el en es esta este hacer la las lo los me mi para por puedo que se un una y".split())

def _plain(value):
    value=unicodedata.normalize("NFKD",str(value or "").casefold())
    return "".join(c for c in value if not unicodedata.combining(c))

def _tokens(value): return {x for x in re.findall(r"[a-z0-9]{2,}",_plain(value)) if x not in STOP}
def _text(item): return " ".join(str(x) for v in item.values() if not isinstance(v,dict) for x in (v if isinstance(v,list) else [v]))
def _best(question,items):
    wanted=_tokens(question);winner=None;score=0
    for item in items:
        current=len(wanted&_tokens(_text(item)))+2*len(wanted&_tokens(item.get("title") or item.get("code") or ""))
        if current>score:winner,score=item,current
    return winner,score
def _steps(values): return "\n".join(f"{n}. {step}" for n,step in enumerate(values or [],1))

def respond(*,question:str,module:str,role:str,allowed_modules=None,knowledge=None,history=None)->dict:
    guide=dict(GUIDES.get(module,DEFAULT_GUIDE));q=_plain(question);actions=[];confidence="confirmed";evidence=[]
    profile=get_platform_profile();allowed_modules=list(allowed_modules or []);knowledge=knowledge or {}
    names=[GUIDES[x]["titulo"] for x in allowed_modules if x in GUIDES];control=knowledge.get("active_control")
    errors=knowledge.get("errors",[]);workflows=knowledge.get("workflows",[]);modules=knowledge.get("modules",[])
    error=next((x for x in errors if _plain(x.get("code")) in q),None);workflow,ws=_best(question,workflows);record,ms=_best(question,modules)
    if any(x in q for x in ("hola","buenos dias","buenas tardes","buenas noches")) and len(_tokens(q))<=3:
        message="¡Hola! Soy LIAM. Puedo explicarte esta pantalla, guiarte paso a paso o ayudarte a entender un error de la plataforma."
    elif any(x in q for x in ("que es esta plataforma","para que sirve")):
        message=f'{profile["description"]} Sirve para centralizar la Base Maestra, el talento humano, salud y nutrición, la gestión integral pedagógica y psicosocial, el calendario, las evidencias, los formatos y el seguimiento autorizado, manteniendo separación por fundación y permisos por rol.'
    elif any(x in q for x in ("que version","version actual")): message=f'La versión configurada actualmente es {profile["version"]}.'
    elif any(x in q for x in ("que modulos","modulos tiene")):
        message=(f"Para el rol {role or 'actual'} hay {len(names)} módulos autorizados: "+", ".join(names)+".") if names else "No encontré módulos autorizados confirmados para esta sesión."
    elif any(x in q for x in ("que puedo hacer","segun mi rol")):
        message=(f"Tu rol actual es {role or 'no identificado'}. Puedes consultar y usar únicamente estas áreas autorizadas: "+", ".join(names)+". LIAM adapta las guías y herramientas a esos permisos.") if names else f"Tu rol actual es {role or 'no identificado'}, pero no encontré áreas autorizadas confirmadas."
    elif any(x in q for x in ("flujo general","como se utiliza la plataforma","como funciona la plataforma")):
        message="Flujo general: 1. Inicia sesión y confirma la fundación. 2. Carga o actualiza las fuentes autorizadas en Base Maestra. 3. Revisa unidades, participantes y talento humano. 4. Consulta el calendario y los entregables. 5. Trabaja en el módulo correspondiente. 6. Carga evidencias o genera borradores. 7. Revisa, confirma y descarga únicamente resultados validados por el sistema y el profesional responsable."
    elif any(x in q for x in ("quien diseno","quien creo","fecha de creacion","presenta la plataforma")):
        if profile['identity_confirmed']:
            message=f'{profile["description"]} Fue diseñada por {profile["designer"]}, su fecha institucional de creación es {profile["created_date"]} y la versión actual es {profile["version"]}.'
        else:
            message=f'{profile["description"]} La autoría y la fecha de creación todavía no han sido confirmadas en la configuración institucional; no debo inventarlas.';confidence="insufficient"
    elif error:
        message=f'{error["code"]}: {error["explanation"]} Qué debes hacer: {error["action"]} Comprueba: {", ".join(error.get("checks",[]))}.';evidence=[{"kind":"error","id":error["code"]}]
    elif control and any(x in q for x in ("como","paso","que hago","pantalla","boton","clic")):
        message=f'{control["title"]}: {control["purpose"]}\n{_steps(control.get("process",[]))}\nSiguiente paso: {control.get("next_step","Confirma el resultado.")}'
        target=control.get("help_id");actions=[{"type":"scroll_to","target":target},{"type":"highlight","target":target}] if target else [];evidence=[{"kind":"control","id":target}]
    elif workflow and ws>=2:
        message=f'{workflow["title"]}:\n{_steps(workflow.get("steps",[]))}\nResultado esperado: {workflow.get("result","Confirma el resultado en pantalla.")}';evidence=[{"kind":"workflow","id":workflow.get("workflow_id")}]
    elif record and ms>=2:
        message=f'{record["title"]}: {record["objective"]}\nRequisitos: {", ".join(record.get("prerequisites",[]))}.\nPaso a paso:\n{_steps(record.get("process",[]))}\nResultado esperado: {record.get("result","Confirma el resultado en pantalla.")}\nSiguiente paso: {record.get("next_step","Revisa el resultado.")}'
        evidence=[{"kind":"module","id":record.get("module_id")}]
    elif any(x in q for x in ("donde","clic","boton")):
        target=control.get("help_id") if control else f"{module}.open";title=control.get("title") if control else guide["titulo"]
        message=f"Te mostraré el acceso registrado de {title}. LIAM no pulsará ni guardará nada por ti.";actions=[{"type":"scroll_to","target":target},{"type":"highlight","target":target}]
    elif any(x in q for x in ("error","fallo","no carga","no descarga","validacion")):
        message="Podemos revisarlo con calma. Comparte el código y el mensaje exactos, sin datos personales, para orientarte con precisión.";confidence="insufficient"
    elif any(x in q for x in ("como","paso","que hago","pantalla")): message=f'{guide.get("proposito",guide["resumen"])}\n{_steps(guide.get("pasos",[]))}'
    else:
        message=f'Estás en {guide["titulo"]}. No encontré una instrucción suficientemente precisa en el Manual Maestro para esa pregunta. Menciona la tarea, el botón o el código del error.';confidence="insufficient"
    safe=redact(message);target=actions[0]["target"] if actions else None
    return {"message":safe,"speech_text":safe,"avatar_state":"guiding" if actions else "speaking","assistant_state":"guiding" if actions else "speaking","avatar":{"gesture":"point_direction" if actions else "show_tablet","expression":"friendly","look_at":target},"movement":{"mode":"walk" if actions else "none","destination":target},"highlight":{"target":target,"mode":"outline"} if actions else None,"tablet":{"type":"message","title":guide["titulo"],"value":safe[:140]},"severity":"info","confidence":confidence,"confirmation_required":False,"suggestions":["Explícame esta pantalla","Guíame paso a paso","¿Qué puedo hacer según mi rol?","Ayúdame con un error"],"actions":actions,"evidence":evidence,"diagnostic":None,"request_id":uuid.uuid4().hex,"module":module,"role":role,"provider":"institutional_static"}
